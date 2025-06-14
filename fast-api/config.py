# config.py
import os

class Config:
    # Flask/FastAPI 세션 등에 사용 (FastAPI에서는 직접 사용하지 않을 수 있음)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-strong-secret-key-should-be-set'

    # Celery 설정
    # 이 값들은 Cloud Run 환경 변수 및 워커 VM 환경 변수로 실제 Redis 주소를 제공해야 함
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/1'

    # Google Cloud Storage (GCS) 설정
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME') or 'my-gcp-speech-test-bucket-882341'
    # GOOGLE_APPLICATION_CREDENTIALS 환경 변수는 GCS 접근에 필요 (VM에서는 서비스 계정 권한으로 대체 가능)

    # STT 서비스 (OpenAI Whisper API 사용 기준)
    STT_SERVICE_PROVIDER = os.environ.get('STT_SERVICE_PROVIDER') or 'openai_whisper_api'
    STT_LANGUAGE_CODE = os.environ.get('STT_LANGUAGE_CODE') or 'ko'

    # OpenAI API 키 설정
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') # Cloud Run/VM 환경 변수로 제공

    # Redis 임시 결과 저장용 (Celery 작업 결과 저장)
    # 이 값들도 Cloud Run 환경 변수 및 워커 VM 환경 변수로 실제 Redis 주소를 제공해야 함
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB_FOR_RESULTS = int(os.environ.get('REDIS_DB_FOR_RESULTS') or 2) # Celery Broker/Backend DB와 다른 번호 사용 권장
    REDIS_RESULT_EXPIRE_SECONDS = int(os.environ.get('REDIS_RESULT_EXPIRE_SECONDS') or 3600) # 1시간

    # --- [신규 추가] 요약용 모델 및 프롬프트 ---
    SUMMARY_MODEL = os.environ.get('SUMMARY_MODEL') or 'gpt-3.5-turbo' # 또는 'gpt-4o' 등
    SUMMARY_PROMPT = os.environ.get('SUMMARY_PROMPT') or 'You are an assistant who summarizes the given text concisely into key points.'

    # (참고) 이전 Google STT 사용 시 설정 (주석 처리 또는 STT_SERVICE_PROVIDER 값에 따라 분기)
    # AUDIO_ENCODING_FOR_STT = 'OGG_OPUS'
    # AUDIO_SAMPLE_RATE_FOR_STT = 48000
    # AUDIO_CHANNEL_COUNT_FOR_STT = 1

    # (참고) 이전 Fast Whisper 자체 호스팅 시 설정 (주석 처리)
    # WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL_SIZE', 'base')
    # WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cpu')
    # WHISPER_COMPUTE_TYPE = os.environ.get('WHISPER_COMPUTE_TYPE', 'int8')


# --- 환경 변수 값 주입의 중요성 ---
# 위 or 'localhost' 같은 기본값은 로컬 개발 환경용입니다.
# Cloud Run 배포 시 또는 워커 VM 실행 시에는 해당 플랫폼의 환경 변수 설정 기능을 통해
# 실제 서비스 엔드포인트(예: Memorystore Redis IP, OpenAI API 키 등)를 주입해야 합니다.
#
# 예시: Cloud Run 환경 변수 설정
# CELERY_BROKER_URL = redis://<Memorystore_Redis_IP>:<Port>/0
# REDIS_HOST = <Memorystore_Redis_IP>
# OPENAI_API_KEY = <실제 OpenAI 키 값 또는 Secret Manager 참조>
# GCS_BUCKET_NAME = <실제 GCS 버킷 이름>
#
# 예시: 워커 VM 환경 변수 설정 (예: /etc/environment 또는 systemd 서비스 파일)
# export CELERY_BROKER_URL="redis://<Memorystore_Redis_IP>:<Port>/0"
# export REDIS_HOST="<Memorystore_Redis_IP>"
# export OPENAI_API_KEY="sk-..."
# export GCS_BUCKET_NAME="<실제 GCS 버킷 이름>"
# (VM의 경우 서비스 계정에 필요한 IAM 권한이 있다면 GOOGLE_APPLICATION_CREDENTIALS는 불필요)