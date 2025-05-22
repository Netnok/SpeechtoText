# tasks.py
from celery import Celery
import os
import redis
import json
import tempfile
import logging

from config import Config

# Google Cloud Storage 클라이언트 (파일 다운로드/삭제용)
from google.cloud import storage as gcs_storage
from google.auth.exceptions import DefaultCredentialsError

# OpenAI 클라이언트 (v1.x.x 이상)
from openai import OpenAI # 'openai' 라이브러리 v1.x.x 이상 필요: pip install --upgrade openai

logger = logging.getLogger(__name__) # Celery 작업용 로거

# --- Celery 앱 설정 ---
celery_app = Celery('tasks',
                    broker=Config.CELERY_BROKER_URL,
                    backend=Config.CELERY_RESULT_BACKEND)

# --- 클라이언트 초기화 (Celery 워커 프로세스 시작 시 한 번 실행) ---
gcs_task_client = None
try:
    gcs_task_client = gcs_storage.Client() # GOOGLE_APPLICATION_CREDENTIALS 환경변수 필요
    logger.info("Celery Worker: GCS Client initialized.")
except DefaultCredentialsError:
    logger.error("Celery Worker: GCP GCS 기본 인증 정보를 찾을 수 없습니다 (GOOGLE_APPLICATION_CREDENTIALS).")
except Exception as e:
    logger.error(f"Celery Worker: GCS 클라이언트 초기화 중 오류 발생: {e}")

redis_task_client = None
try:
    redis_task_client = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=Config.REDIS_RESULT_DB, decode_responses=True
    )
    redis_task_client.ping()
    logger.info(f"Celery Worker: Redis (for results on db {Config.REDIS_RESULT_DB}) connected.")
except Exception as e:
    logger.error(f"Celery Worker: Redis (for results) 연결 오류: {e}")

# OpenAI API 클라이언트 초기화
openai_client = None
if Config.OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("Celery Worker: OpenAI Client initialized.")
    except Exception as e:
        logger.error(f"Celery Worker: OpenAI Client 초기화 중 오류 발생: {e}")
else:
    logger.error("Celery Worker: OPENAI_API_KEY가 설정되지 않았습니다. Config 또는 환경 변수를 확인하세요.")


# --- 헬퍼 함수 ---
def store_result_in_redis(job_id, data_dict):
    if redis_task_client:
        result_key = f"stt_result:{job_id}"
        try:
            redis_task_client.setex(result_key, Config.REDIS_RESULT_EXPIRE_SECONDS, json.dumps(data_dict))
            logger.info(f"Job {job_id}: Result stored in Redis. Key: {result_key}")
        except Exception as e:
            logger.error(f"Job {job_id}: Failed to store result in Redis: {e}")
    else:
        logger.warning(f"Job {job_id}: Redis client (for results) not available. Cannot store result.")

def delete_gcs_file(bucket_name, object_name, job_id="N/A"):
    if gcs_task_client and bucket_name and object_name:
        try:
            bucket = gcs_task_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            if blob.exists():
                blob.delete()
                logger.info(f"Job {job_id}: Deleted GCS file: gs://{bucket_name}/{object_name}")
            else:
                logger.warning(f"Job {job_id}: GCS file not found for deletion: gs://{bucket_name}/{object_name}")
        except Exception as e:
            logger.error(f"Job {job_id}: Error deleting GCS file gs://{bucket_name}/{object_name}: {e}")
    else:
        if not gcs_task_client: logger.warning(f"Job {job_id}: GCS client not available for deletion.")
        if not bucket_name or not object_name: logger.warning(f"Job {job_id}: Bucket/object name missing for GCS deletion.")


# --- Celery 작업 정의 (OpenAI Whisper API v1.x.x 사용) ---
@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def process_audio_with_openai_whisper_task(self, job_id, gcs_bucket_for_audio, gcs_object_key_for_audio, audio_content_type_hint=None):
    task_log_prefix = f"Celery Task ID: {self.request.id} - JobID: {job_id}"
    logger.info(f"{task_log_prefix} - OpenAI Whisper API STT 처리 시작, GCS Path: gs://{gcs_bucket_for_audio}/{gcs_object_key_for_audio}")

    if not openai_client: # OpenAI 클라이언트가 초기화되지 않았으면 작업 실패 처리
        error_msg = "OpenAI Client is not initialized in Celery worker. Check API Key."
        logger.error(f"{task_log_prefix}: {error_msg}")
        store_result_in_redis(job_id, {"status": "Failed", "error": error_msg})
        delete_gcs_file(gcs_bucket_for_audio, gcs_object_key_for_audio, job_id)
        return error_msg

    if not gcs_task_client: # GCS 클라이언트 없으면 파일 다운로드 불가
        error_msg = "GCS client not initialized in Celery worker."
        logger.error(f"{task_log_prefix}: {error_msg}")
        store_result_in_redis(job_id, {"status": "Failed", "error": error_msg})
        return error_msg # GCS 파일 삭제는 GCS 클라이언트가 없으므로 시도하지 않음

    # Redis에 'Processing' 상태 먼저 기록
    store_result_in_redis(job_id, {"status": "Processing"})

    temp_audio_file_path = None
    try:
        # 1. GCS에서 오디오 파일 다운로드
        bucket = gcs_task_client.bucket(gcs_bucket_for_audio)
        blob = bucket.blob(gcs_object_key_for_audio)
        
        if not blob.exists():
            error_msg = f"Audio file not found in GCS: gs://{gcs_bucket_for_audio}/{gcs_object_key_for_audio}"
            logger.error(f"{task_log_prefix}: {error_msg}")
            store_result_in_redis(job_id, {"status": "Failed", "error": error_msg})
            return error_msg

        # 파일 확장자를 유지하며 임시 파일 생성 (OpenAI API는 파일 객체를 받으므로)
        _, file_extension = os.path.splitext(gcs_object_key_for_audio)
        # delete=False로 해야 with 블록 벗어나도 파일 유지, finally에서 직접 삭제
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            temp_audio_file_path = tmp_file.name
        
        blob.download_to_filename(temp_audio_file_path)
        logger.info(f"{task_log_prefix}: Audio downloaded from GCS to: {temp_audio_file_path}")

        # 2. OpenAI Whisper API로 STT 처리 (OpenAI 라이브러리 v1.x.x 방식)
        final_text = ""
        detected_language_api = Config.STT_LANGUAGE_CODE # 기본값

        with open(temp_audio_file_path, "rb") as audio_file_opened:
            logger.info(f"{task_log_prefix}: Sending audio to OpenAI Whisper API. Language hint: {Config.STT_LANGUAGE_CODE}")
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1", # Whisper API에서 사용하는 모델명
                file=audio_file_opened, # 파일 객체 전달
                language=Config.STT_LANGUAGE_CODE if Config.STT_LANGUAGE_CODE else None, # 'ko' 등, None이면 자동 감지
                response_format="verbose_json" # 'json', 'text', 'srt', 'verbose_json', 'vtt'
            )
        # response_format="verbose_json" 사용 시 transcript_response.text 로 접근
        # response_format="json" 사용 시 transcript_response['text'] 로 접근 (구버전 방식)
        # 최신 라이브러리(v1.x.x)는 Pydantic 모델을 반환하므로 객체 속성으로 접근
        
        logger.info(f"{task_log_prefix}: OpenAI Whisper API Raw Response (object type): {type(transcription)}")
        # verbose_json 응답 객체 구조 확인 후 필요한 정보 추출
        # 예: final_text = transcription.text
        #     detected_language_api = transcription.language
        #     duration = transcription.duration
        #     segments = transcription.segments (타임스탬프 등 상세 정보)
        
        if hasattr(transcription, 'text'):
            final_text = transcription.text.strip()
            if hasattr(transcription, 'language'): # verbose_json 선택 시 language 필드 존재
                detected_language_api = transcription.language
        elif isinstance(transcription, dict) and "text" in transcription: # 혹시 dict로 오는 경우 (이전 버전 호환성)
            final_text = transcription.get("text", "").strip()
            # detected_language_api = transcription.get("language", Config.STT_LANGUAGE_CODE)
        else: # 예상치 못한 응답 형식
            logger.warning(f"{task_log_prefix}: Unexpected OpenAI API response format: {transcription}")


        # 3. 결과 Redis에 저장
        result_data = {
            "status": "Completed",
            "transcription": final_text,
            "detected_language": detected_language_api
        }
        if not final_text: # 텍스트는 없지만 언어는 감지된 경우 등
             result_data["error_detail"] = "Whisper API 결과가 비어있거나 음성이 감지되지 않았습니다."
        
        store_result_in_redis(job_id, result_data)
        logger.info(f"{task_log_prefix}: OpenAI Whisper STT Completed. Text length: {len(final_text)}")
        
        return f"Job {job_id} successfully processed with OpenAI Whisper."

    except openai.APIError as e_openai: # OpenAI API 자체 에러 (예: 인증, 과금, 서버 문제 등)
        error_message_for_redis = f"OpenAI API Error: {type(e_openai).__name__} - Status: {e_openai.status_code if hasattr(e_openai, 'status_code') else 'N/A'} - Message: {str(e_openai)}"
        logger.error(f"{task_log_prefix} OpenAI API Error: {e_openai}", exc_info=True)
        store_result_in_redis(job_id, {"status": "Failed", "error": error_message_for_redis})
        return f"Job {job_id} failed with OpenAI API: {error_message_for_redis}"
    except Exception as exc: # 그 외 일반적인 예외
        error_message_for_redis = f"Error in OpenAI Whisper STT task: {type(exc).__name__} - {str(exc)}"
        logger.error(f"{task_log_prefix} General Error: {exc}", exc_info=True)
        store_result_in_redis(job_id, {"status": "Failed", "error": error_message_for_redis})
        return f"Job {job_id} failed: {error_message_for_redis}"
    
    finally:
        # 4. 임시 로컬 오디오 파일 삭제
        if temp_audio_file_path and os.path.exists(temp_audio_file_path):
            try:
                os.remove(temp_audio_file_path)
                logger.info(f"{task_log_prefix}: Deleted temporary local audio file: {temp_audio_file_path}")
            except Exception as e_rem:
                logger.error(f"{task_log_prefix}: Error deleting temporary local file {temp_audio_file_path}: {e_rem}")
        
        # 5. 원본 GCS 오디오 파일 삭제
        delete_gcs_file(gcs_bucket_for_audio, gcs_object_key_for_audio, job_id)