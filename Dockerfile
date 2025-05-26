FROM python:3.11-slim

# 작업 디렉토리 생성
WORKDIR /app

# requirements.txt 복사 및 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 코드 복사
COPY . .

# 8080 포트 노출
EXPOSE 8080

# FastAPI(Uvicorn) 서버 실행 (호스트 0.0.0.0:8080)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
