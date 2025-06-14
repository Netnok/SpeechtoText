# Dockerfile
FROM python:3.12-slim 
# 또는 사용하시는 Python 버전에 맞춰서 (예: 3.12-slim)

# 작업 디렉토리 설정
WORKDIR /app

# 환경 변수 설정 (버퍼링 없이 즉시 로그 출력, Python 경로)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 파이썬 의존성 패키지 설치
# requirements.txt 파일만 먼저 복사하여 Docker 캐시를 효율적으로 사용
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체 파일 복사 (이제 .dockerignore에 의해 venv 등은 제외됨)
COPY . .

# Cloud Run이 자동으로 PORT 환경 변수를 주입합니다 (보통 8080).
# Gunicorn이 이 포트를 사용하도록 설정합니다.
ENV PORT=8080

# Uvicorn을 Gunicorn 워커로 실행
# Gunicorn은 requirements.txt에 포함되어야 합니다.
CMD ["/bin/sh", "-c", "gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app --bind \"0.0.0.0:${PORT}\" --forwarded-allow-ips=\"*\" --access-logfile - --error-logfile -"]