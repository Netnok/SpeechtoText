# main.py
from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import uuid
import redis
import json
import logging

# 프로젝트 루트의 config.py, tasks.py (Celery 작업) 임포트
from config import Config
from tasks import process_audio_with_openai_whisper_task # 변경된 Celery 작업 함수 임포트

# GCS 관련
from google.cloud import storage as gcs_storage
from google.auth.exceptions import DefaultCredentialsError

# 파일명 보안
from werkzeug.utils import secure_filename

# --- 로거 설정 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI 앱 생성 ---
app = FastAPI(title="Audio-to-Text Service (OpenAI Whisper API)")

# --- 템플릿 설정 ---
templates = Jinja2Templates(directory="templates") # main.py와 같은 레벨에 templates 폴더

# --- GCS 클라이언트 초기화 ---
gcs_client = None
gcs_bucket = None
if Config.GCS_BUCKET_NAME and Config.GCS_BUCKET_NAME != 'your-actual-gcs-bucket-name':
    try:
        gcs_client = gcs_storage.Client() # GOOGLE_APPLICATION_CREDENTIALS 환경 변수 필요
        gcs_bucket = gcs_client.bucket(Config.GCS_BUCKET_NAME)
        logger.info(f"GCS Client initialized for bucket: {Config.GCS_BUCKET_NAME}")
    except DefaultCredentialsError:
        logger.error("GCP 기본 인증 정보를 찾을 수 없습니다. GOOGLE_APPLICATION_CREDENTIALS 환경 변수를 확인하세요.")
    except Exception as e:
        logger.error(f"GCS 클라이언트 초기화 중 오류 발생: {e}")
else:
    logger.warning("GCS_BUCKET_NAME이 설정되지 않았거나 플레이스홀더 값입니다. GCS 기능이 제한됩니다.")


# --- Redis 클라이언트 초기화 (STT 결과 임시 저장용) ---
redis_client = None
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_RESULT_DB,
        decode_responses=True
    )
    redis_client.ping()
    logger.info(f"Redis (for results on db {Config.REDIS_RESULT_DB}) connected.")
except Exception as e:
    logger.error(f"Redis (for results) connection error: {e}")


# --- 허용 파일 확장자 (Whisper API는 다양한 포맷 지원) ---
ALLOWED_EXTENSIONS = {'webm', 'wav', 'ogg', 'mp3', 'm4a', 'flac', 'mp4', 'mpeg', 'mpga'}

def allowed_file(filename: str):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 라우트 정의 ---
@app.get("/", response_class=HTMLResponse, name="get_upload_form_route", tags=["Pages"])
async def get_upload_form_route(request: Request):
    """파일 업로드(녹음) 폼을 보여주는 기본 페이지"""
    uploader_ip = request.client.host 
    return templates.TemplateResponse("recorder_page_with_upload.html", {"request": request, "uploader_ip": uploader_ip})

@app.post("/upload", name="upload_and_process_file_route", tags=["Actions"])
async def upload_and_process_file_route(request: Request, file: UploadFile = File(...)):
    """음성 파일을 받아 GCS에 업로드하고 Celery STT 작업을 시작합니다."""
    uploader_ip = request.client.host 
    
    if not gcs_bucket:
        logger.error("GCS 버킷이 준비되지 않아 파일 업로드를 진행할 수 없습니다.")
        raise HTTPException(status_code=503, detail="파일 저장소(GCS)가 준비되지 않았습니다.")
    if not redis_client:
        logger.error("Redis 클라이언트가 준비되지 않아 작업 상태를 저장할 수 없습니다.")
        raise HTTPException(status_code=503, detail="내부 결과 저장소(Redis)가 준비되지 않았습니다.")

    if not file or not file.filename:
        logger.warning(f"IP {uploader_ip}: 업로드 시도 - 파일이 없거나 파일 이름이 없습니다.")
        raise HTTPException(status_code=400, detail="파일이 선택되지 않았거나 파일 이름이 없습니다.")
    
    original_filename_secured = secure_filename(file.filename)

    if not allowed_file(original_filename_secured):
        logger.warning(f"IP {uploader_ip}: 업로드 시도 - 허용되지 않는 파일 형식: {original_filename_secured}")
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다: '{original_filename_secured}'. (지원: {', '.join(ALLOWED_EXTENSIONS)})")

    job_id = uuid.uuid4().hex
    gcs_object_name = f"audio_uploads_for_whisper/{job_id}/{original_filename_secured}" # GCS 저장 경로

    try:
        contents = await file.read()
        if not contents:
            logger.warning(f"Job {job_id} (IP {uploader_ip}): 업로드된 파일 '{original_filename_secured}'이 비어있습니다.")
            raise HTTPException(status_code=400, detail="업로드된 파일이 비어있습니다.")

        blob = gcs_bucket.blob(gcs_object_name)
        file_content_type = file.content_type or f"audio/{original_filename_secured.rsplit('.', 1)[1].lower()}"
        
        blob.upload_from_string(contents, content_type=file_content_type)
        # GCS URI는 Whisper API에 직접 사용하지 않지만, 로깅이나 다른 용도로 남겨둘 수 있음
        # gcs_uri = f"gs://{Config.GCS_BUCKET_NAME}/{gcs_object_name}" 
        logger.info(f"Job {job_id}: File '{original_filename_secured}' (Type: {file_content_type}) uploaded to GCS: gs://{Config.GCS_BUCKET_NAME}/{gcs_object_name}")

        # Celery 작업 호출 (OpenAI Whisper API 사용 작업)
        process_audio_with_openai_whisper_task.delay(
            job_id,
            Config.GCS_BUCKET_NAME, # GCS 버킷명 전달
            gcs_object_name,        # GCS 객체 키 전달
            file_content_type       # content_type 힌트 전달 (로깅/참고용)
        )
        logger.info(f"Job {job_id}: Celery OpenAI Whisper STT task initiated for GCS object: {gcs_object_name}")

        return RedirectResponse(url=request.url_for('get_result_page_route', job_id=job_id), status_code=303)

    except Exception as e:
        logger.error(f"Job {job_id}: Upload or Celery task initiation error: {e}", exc_info=True)
        if 'blob' in locals() and blob and gcs_bucket.get_blob(gcs_object_name):
            try:
                blob.delete()
                logger.info(f"Job {job_id}: Cleaned up GCS file due to error: {gcs_object_name}")
            except Exception as e_del:
                logger.error(f"Job {job_id}: Error cleaning up GCS file {gcs_object_name}: {e_del}")
        raise HTTPException(status_code=500, detail=f"서버에서 파일 처리 중 오류가 발생했습니다.")


@app.get("/result/{job_id}", response_class=HTMLResponse, name="get_result_page_route", tags=["Pages"])
async def get_result_page_route(request: Request, job_id: str):
    """특정 Job ID에 대한 STT 결과를 보여주는 페이지"""
    current_uploader_ip = request.client.host # 로깅이나 임시 UI 표시용
    
    if not redis_client:
        logger.error(f"Job {job_id}: Redis 클라이언트가 준비되지 않아 결과를 조회할 수 없습니다.")
        return templates.TemplateResponse("result_display_stateless.html", {
            "request": request, "job_id": job_id, "status": "Error",
            "error_message": "결과 저장소(Redis)에 연결할 수 없습니다.", "uploader_ip": current_uploader_ip
        })

    result_key = f"stt_result:{job_id}"
    result_data_json_str = redis_client.get(result_key)
    
    template_context = {"request": request, "job_id": job_id, "uploader_ip": current_uploader_ip}

    if result_data_json_str:
        try:
            result_data = json.loads(result_data_json_str)
            status = result_data.get("status")
            template_context["status"] = status
            
            if status == "Completed":
                template_context["transcription"] = result_data.get("transcription")
                template_context["detected_language"] = result_data.get("detected_language")
                if result_data.get("error_detail"): 
                    template_context["warning_message"] = result_data.get("error_detail")
                redis_client.delete(result_key) 
                logger.info(f"Job {job_id}: Result fetched by IP {current_uploader_ip} and removed from Redis.")
            elif status == "Failed":
                template_context["error_message"] = result_data.get("error")
                redis_client.delete(result_key)
                logger.info(f"Job {job_id}: Failed status fetched by IP {current_uploader_ip} and removed from Redis.")
            else: # Processing
                logger.info(f"Job {job_id}: Status is '{status}', will refresh for IP {current_uploader_ip}.")
        
        except json.JSONDecodeError:
            logger.error(f"Job {job_id}: Failed to decode JSON from Redis: {result_data_json_str}")
            template_context["status"] = "Error"
            template_context["error_message"] = "결과 데이터 형식 오류."
            redis_client.delete(result_key)
        except Exception as e:
            logger.error(f"Job {job_id}: Error processing result from Redis: {e}")
            template_context["status"] = "Error"
            template_context["error_message"] = "결과 처리 중 오류 발생."
    else:
        logger.info(f"Job {job_id}: No result found in Redis for IP {current_uploader_ip}.")
        template_context["status"] = "Pending or Expired"

    return templates.TemplateResponse("result_display_stateless.html", template_context)

# Uvicorn으로 실행: uvicorn main:app --reload --host 0.0.0.0 --port 8000