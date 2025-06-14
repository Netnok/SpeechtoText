# main.py
from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
import redis
import json
import logging

from config import Config
# 두 가지 작업을 모두 임포트
from tasks import process_audio_with_openai_whisper_task, summarize_text_with_gpt_task

from google.cloud import storage as gcs_storage
from google.auth.exceptions import DefaultCredentialsError
from werkzeug.utils import secure_filename

# --- 로거, 앱 생성, CORS 설정, 클라이언트 초기화 (이전 #58번 답변과 동일) ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: [%(asctime)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Backend API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite (React) 개발 서버 주소
    "http://127.0.0.1:5173",
    "https://my-stt-app-843376384818.asia-northeast3.run.app"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 위 목록에 있는 출처로부터의 요청을 허용
    allow_credentials=True,      # 쿠키를 포함한 요청 허용
    allow_methods=["*"],         # 모든 HTTP 메소드(GET, POST 등) 허용
    allow_headers=["*"],         # 모든 HTTP 헤더 허용
)
# --- C

gcs_client = None
gcs_bucket = None
if Config.GCS_BUCKET_NAME:
    try:
        gcs_client = gcs_storage.Client()
        gcs_bucket = gcs_client.bucket(Config.GCS_BUCKET_NAME)
        logger.info(f"GCS Client initialized for bucket: {Config.GCS_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"GCS 클라이언트 초기화 중 오류 발생: {e}", exc_info=True)
else:
    logger.warning("GCS_BUCKET_NAME이 설정되지 않았습니다.")

redis_client = None
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=Config.REDIS_DB_FOR_RESULTS, decode_responses=True
    )
    redis_client.ping()
    logger.info(f"Redis (for results on db {Config.REDIS_DB_FOR_RESULTS}) connected.")
except Exception as e:
    logger.error(f"Redis (for results) 연결 오류: {e}", exc_info=True)

ALLOWED_EXTENSIONS = {'webm', 'wav', 'ogg', 'mp3', 'm4a'}

def allowed_file(filename: str):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Pydantic 모델 정의 ---
class SummarizeRequest(BaseModel):
    jobId: str # STT 작업의 원래 Job ID
    text: str

# --- API 엔드포인트 정의 ---
@app.get("/", tags=["Status"])
async def read_root():
    return {"status": "ok", "message": "AI Agent Backend is running."}

@app.post("/upload", name="upload_and_process_file", tags=["STT"])
async def upload_and_process_file(file: UploadFile = File(...)):
    # ... (이전 #58 답변의 /upload 라우트 내용과 거의 동일, Celery 작업 함수 이름만 확인) ...
    if not gcs_bucket or not redis_client:
        raise HTTPException(status_code=503, detail="백엔드 서비스가 준비되지 않았습니다.")
    
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="파일이 선택되지 않았습니다.")
    
    original_filename_secured = secure_filename(file.filename)
    if not allowed_file(original_filename_secured):
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다: {original_filename_secured}")

    job_id = uuid.uuid4().hex
    gcs_object_name = f"audio_uploads/{job_id}/{original_filename_secured}"

    try:
        contents = await file.read()
        if not contents: raise HTTPException(status_code=400, detail="업로드된 파일이 비어있습니다.")

        blob = gcs_bucket.blob(gcs_object_name)
        blob.upload_from_string(contents, content_type=file.content_type)
        logger.info(f"Job {job_id}: File '{original_filename_secured}' uploaded to GCS.")

        process_audio_with_openai_whisper_task.delay(
            job_id, Config.GCS_BUCKET_NAME, gcs_object_name, file.content_type
        )
        logger.info(f"Job {job_id}: Celery STT task initiated.")
        
        return JSONResponse(status_code=202, content={"job_id": job_id, "message": "STT 작업이 시작되었습니다."})

    except Exception as e:
        logger.error(f"Job {job_id}: Upload error: {e}", exc_info=True)
        if 'blob' in locals() and blob.exists(): blob.delete()
        raise HTTPException(status_code=500, detail="서버에서 파일 처리 중 오류가 발생했습니다.")


@app.post("/summarize", name="summarize_text", tags=["Summarization"])
async def summarize_text_route(request: SummarizeRequest):
    """텍스트를 받아 요약 작업을 시작하고, 요약 작업용 Job ID를 반환합니다."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="백엔드 서비스가 준비되지 않았습니다.")
        
    original_job_id = request.jobId
    text_to_summarize = request.text
    summary_job_key = f"summary:{original_job_id}" # Redis 키 구분을 위한 접두사

    if not text_to_summarize or not text_to_summarize.strip():
        raise HTTPException(status_code=400, detail="요약을 위한 텍스트가 비어있습니다.")

    try:
        summarize_text_with_gpt_task.delay(original_job_id, text_to_summarize)
        logger.info(f"Job {original_job_id}: Celery Summarization task initiated.")
        
        return JSONResponse(status_code=202, content={"job_id": summary_job_key, "message": "요약 작업이 시작되었습니다."})

    except Exception as e:
        logger.error(f"Job {original_job_id}: Summarization task initiation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버에서 요약 작업 시작 중 오류가 발생했습니다.")


@app.get("/result/{job_id_key}", name="get_task_result", tags=["Results"])
async def get_task_result_route(job_id_key: str):
    """특정 Job ID Key에 대한 작업 상태와 결과를 JSON으로 반환합니다."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="결과 저장소에 연결할 수 없습니다.")
    
    # job_id_key는 'stt_result:...' 또는 'summary:...' 형태의 Redis 키에서 접두사를 제외한 ID 부분
    # 프론트에서 /result/job123, /result/summary:job123 형태로 요청
    redis_key = f"stt_result:{job_id_key}" # 기본은 STT 결과 키
    if job_id_key.startswith("summary:"):
        # 프론트엔드가 'summary:job123' 형태로 요청하면 Redis 키가 'stt_result:summary:job123' 이 됨.
        # 따라서 프론트에서는 'summary:' 접두사를 붙여서 요청하고, 여기서는 그 키를 그대로 사용
        redis_key = job_id_key.replace("summary:", "stt_result:summary:", 1) # 키 형식 통일
        # 아니면 tasks.py에서 summary 키를 stt_result:summary:jobid 로 저장해야함
        # tasks.py의 store_result_in_redis 키를 "stt_result:"로 통일했으므로,
        # 프론트에서 요약 결과 요청 시 'summary:job123'을 보내면 여기서 키를 재구성
        redis_key = f"stt_result:{job_id_key}"

    result_data_json_str = redis_client.get(redis_key)
    
    if result_data_json_str:
        result_data = json.loads(result_data_json_str)
        status = result_data.get("status")

        if status in ["Completed", "Failed"]:
            redis_client.delete(redis_key)
            logger.info(f"Result for key '{redis_key}' fetched and removed from Redis.")
        
        return JSONResponse(status_code=200, content=result_data)
    else:
        return JSONResponse(status_code=202, content={"status": "Processing", "message": "작업이 아직 처리 중이거나 결과를 찾을 수 없습니다."})