# tasks.py
from celery import Celery
import os
import redis
import json
import tempfile
import logging

from config import Config

from google.cloud import storage as gcs_storage
from google.auth.exceptions import DefaultCredentialsError
from openai import OpenAI, APIError

logger = logging.getLogger(__name__)

# --- Celery 앱 설정 ---
celery_app = Celery('tasks',
                    broker=Config.CELERY_BROKER_URL,
                    backend=Config.CELERY_RESULT_BACKEND)

# --- 클라이언트 초기화 ---
gcs_task_client = None
try:
    gcs_task_client = gcs_storage.Client()
    logger.info("Celery Worker: GCS Client initialized.")
except DefaultCredentialsError:
    logger.error("Celery Worker: GCP GCS 기본 인증 정보를 찾을 수 없습니다 (GOOGLE_APPLICATION_CREDENTIALS).")
except Exception as e:
    logger.error(f"Celery Worker: GCS 클라이언트 초기화 중 오류 발생: {e}", exc_info=True)

redis_task_client = None
try:
    redis_task_client = redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=Config.REDIS_DB_FOR_RESULTS, decode_responses=True
    )
    redis_task_client.ping()
    logger.info(f"Celery Worker: Redis (for results on db {Config.REDIS_DB_FOR_RESULTS}) connected.")
except Exception as e:
    logger.error(f"Celery Worker: Redis (for results) 연결 오류: {e}", exc_info=True)

openai_client = None
if Config.OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("Celery Worker: OpenAI Client initialized.")
    except Exception as e:
        logger.error(f"Celery Worker: OpenAI Client 초기화 중 오류 발생: {e}", exc_info=True)
else:
    logger.error("Celery Worker: OPENAI_API_KEY가 설정되지 않았습니다.")

# --- 헬퍼 함수 ---
def store_result_in_redis(job_id_key, data_dict):
    if redis_task_client:
        result_key = f"stt_result:{job_id_key}" # Key prefix 통일
        try:
            redis_task_client.setex(result_key, Config.REDIS_RESULT_EXPIRE_SECONDS, json.dumps(data_dict))
            logger.info(f"Job {job_id_key}: Result stored in Redis. Key: {result_key}")
        except Exception as e:
            logger.error(f"Job {job_id_key}: Failed to store result in Redis: {e}", exc_info=True)
    else:
        logger.warning(f"Job {job_id_key}: Redis client not available. Cannot store result.")

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
            logger.error(f"Job {job_id}: Error deleting GCS file gs://{bucket_name}/{object_name}: {e}", exc_info=True)
    else:
        if not gcs_task_client: logger.warning(f"Job {job_id}: GCS client not available for GCS deletion.")
        if not bucket_name or not object_name: logger.warning(f"Job {job_id}: Bucket/object name missing for GCS deletion.")

# --- Celery 작업 정의 1: Whisper STT ---
@celery_app.task(bind=True, name='tasks.process_audio_with_openai_whisper_task', max_retries=1, default_retry_delay=60)
def process_audio_with_openai_whisper_task(self, job_id, gcs_bucket_for_audio, gcs_object_key_for_audio, audio_content_type_hint=None):
    task_log_prefix = f"Celery Task ID: {self.request.id} - JobID: {job_id}"
    logger.info(f"{task_log_prefix} - OpenAI Whisper API STT 처리 시작, GCS Path: gs://{gcs_bucket_for_audio}/{gcs_object_key_for_audio}")
    
    if not openai_client or not gcs_task_client:
        error_msg = "A required client (OpenAI or GCS) is not initialized in Celery worker."
        logger.error(f"{task_log_prefix}: {error_msg}")
        store_result_in_redis(job_id, {"status": "Failed", "error": error_msg})
        if gcs_task_client: delete_gcs_file(gcs_bucket_for_audio, gcs_object_key_for_audio, job_id)
        return error_msg
    
    store_result_in_redis(job_id, {"status": "Processing"})
    
    temp_audio_file_path = None
    try:
        bucket = gcs_task_client.bucket(gcs_bucket_for_audio)
        blob = bucket.blob(gcs_object_key_for_audio)
        if not blob.exists():
            raise FileNotFoundError(f"Audio file not found in GCS: gs://{gcs_bucket_for_audio}/{gcs_object_key_for_audio}")

        _, file_extension = os.path.splitext(gcs_object_key_for_audio)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            temp_audio_file_path = tmp_file.name
        
        blob.download_to_filename(temp_audio_file_path)
        logger.info(f"{task_log_prefix}: Audio downloaded to: {temp_audio_file_path}")

        with open(temp_audio_file_path, "rb") as audio_file_opened:
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_opened,
                language=Config.STT_LANGUAGE_CODE if Config.STT_LANGUAGE_CODE else None,
                response_format="verbose_json"
            )
        
        final_text = getattr(transcription, 'text', '').strip()
        detected_language_api = getattr(transcription, 'language', Config.STT_LANGUAGE_CODE)
        
        result_data = {
            "status": "Completed", "transcription": final_text, "detected_language": detected_language_api
        }
        if not final_text:
             result_data["error_detail"] = "Whisper API 결과가 비어있거나 음성이 감지되지 않았습니다."
        
        store_result_in_redis(job_id, result_data)
        logger.info(f"{task_log_prefix}: OpenAI Whisper STT Completed.")
        return f"Job {job_id} successfully processed with OpenAI Whisper."

    except Exception as exc:
        error_message = f"Error in Whisper STT task: {type(exc).__name__} - {str(exc)}"
        logger.error(f"{task_log_prefix} Error: {exc}", exc_info=True)
        store_result_in_redis(job_id, {"status": "Failed", "error": error_message})
        return f"Job {job_id} failed: {error_message}"
    
    finally:
        if temp_audio_file_path and os.path.exists(temp_audio_file_path):
            os.remove(temp_audio_file_path)
        delete_gcs_file(gcs_bucket_for_audio, gcs_object_key_for_audio, job_id)

# --- Celery 작업 정의 2: GPT 요약 ---
@celery_app.task(bind=True, name='tasks.summarize_text_with_gpt_task', max_retries=1, default_retry_delay=60)
def summarize_text_with_gpt_task(self, job_id, text_to_summarize):
    task_log_prefix = f"Celery Task ID: {self.request.id} - JobID: {job_id}"
    summary_job_key = f"summary:{job_id}"
    logger.info(f"{task_log_prefix} - OpenAI Chat-GPT 요약 처리 시작")

    if not openai_client:
        error_msg = "OpenAI Client is not initialized in Celery worker."
        logger.error(f"{task_log_prefix}: {error_msg}")
        store_result_in_redis(summary_job_key, {"status": "Failed", "error": error_msg})
        return error_msg

    if not text_to_summarize or not text_to_summarize.strip():
        error_msg = "Input text for summarization is empty."
        logger.warning(f"{task_log_prefix}: {error_msg}")
        store_result_in_redis(summary_job_key, {"status": "Completed", "summary": "", "detail": error_msg})
        return f"Job {job_id} completed with empty summary as input was empty."

    store_result_in_redis(summary_job_key, {"status": "Processing"})

    try:
        system_prompt = Config.SUMMARY_PROMPT
        model_to_use = Config.SUMMARY_MODEL

        logger.info(f"{task_log_prefix}: Sending text (length: {len(text_to_summarize)}) to '{model_to_use}' for summarization.")
        
        chat_completion = openai_client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_to_summarize}
            ],
            temperature=0.5
        )

        summary_text = chat_completion.choices[0].message.content.strip()
        logger.info(f"{task_log_prefix}: Summarization completed. Summary length: {len(summary_text)}")

        result_data = {"status": "Completed", "summary": summary_text}
        store_result_in_redis(summary_job_key, result_data)
        return f"Job {job_id} successfully summarized."

    except APIError as e_openai:
        error_message = f"OpenAI API Error: {type(e_openai).__name__} - Status: {e_openai.status_code if hasattr(e_openai, 'status_code') else 'N/A'} - {str(e_openai)}"
        logger.error(f"{task_log_prefix} OpenAI API Error: {e_openai}", exc_info=True)
        store_result_in_redis(summary_job_key, {"status": "Failed", "error": error_message})
        return f"Job {job_id} failed with OpenAI API: {error_message}"
    except Exception as exc:
        error_message = f"Error in summarization task: {type(exc).__name__} - {str(exc)}"
        logger.error(f"{task_log_prefix} General Error: {exc}", exc_info=True)
        store_result_in_redis(summary_job_key, {"status": "Failed", "error": error_message})
        return f"Job {job_id} failed: {error_message}"