# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secure-fastapi-secret-key-A1B2C3D4'

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/1'

    # GCS 설정은 파일 임시 저장 및 삭제에 계속 사용
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME') or 'my-gcp-speech-test-bucket-882341'
    # GOOGLE_APPLICATION_CREDENTIALS 환경 변수는 GCS 접근에 계속 필요

    # --- STT 서비스 설정 (OpenAI Whisper API 사용) ---
    STT_SERVICE_PROVIDER = 'openai_whisper_api'
    # Whisper API는 언어 자동 감지 기능이 뛰어나지만, 명시적으로 'ko'를 전달할 수도 있습니다.
    # API 호출 시 language 파라미터로 전달하므로 config에서는 필수는 아닐 수 있음.
    STT_LANGUAGE_CODE = 'ko' # API 호출 시 language='ko'로 전달

    # --- OpenAI API 키 설정 ---
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') # <<-- 환경 변수에서 로드!

    # Redis 임시 결과 저장용
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_RESULT_DB = int(os.environ.get('REDIS_RESULT_DB') or 2)
    REDIS_RESULT_EXPIRE_SECONDS = int(os.environ.get('REDIS_RESULT_EXPIRE_SECONDS') or 3600)