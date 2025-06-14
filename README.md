# 🤖 AI Agent: 음성-텍스트 변환 및 요약 서비스

실시간으로 녹음되거나 업로드된 음성 파일을 텍스트로 변환하고,  
생성된 텍스트를 AI 모델을 통해 요약하는 기능을 제공하는 웹 애플리케이션입니다.  
비동기 처리 아키텍처를 통해 긴 오디오 파일도 안정적으로 처리할 수 있도록 설계되었습니다.

---

## ✨ 주요 기능

- **브라우저 기반 음성 녹음**  
  웹 페이지에서 직접 마이크를 사용하여 음성을 녹음합니다.

- **오디오 파일 업로드**  
  미리 준비된 오디오 파일을 업로드하여 처리합니다.

- **비동기 STT 처리**  
  OpenAI Whisper API를 사용하여 음성을 텍스트로 변환합니다.  
  Celery를 통해 백그라운드에서 처리되어 사용자는 오래 기다릴 필요가 없습니다.

- **텍스트 요약**  
  변환된 텍스트를 OpenAI GPT 모델(`gpt-3.5-turbo`)을 사용하여 핵심 내용으로 요약합니다.

- **실시간 상태 업데이트**  
  프론트엔드에서 주기적인 폴링을 통해 처리 상태(처리 중, 완료, 실패)를 확인합니다.

- **Stateless 아키텍처**  
  사용자 데이터나 작업 이력을 서버에 저장하지 않아 개인정보 보호에 유리합니다.

---

## 🛠️ 기술 스택

| 구분              | 기술                                                    |
|-------------------|---------------------------------------------------------|
| **Backend**       | Python, FastAPI, Uvicorn, Gunicorn, Celery, Redis, OpenAI API |
| **Frontend**      | React, TypeScript, Vite, Axios, Tailwind CSS            |
| **Cloud & Infra** | Google Cloud Platform, Google Cloud Storage, Docker    |

---

## 📁 프로젝트 구조

```
record-ai-agent/
├── client/              # React 프론트엔드
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── .env.development  (생성 필요)
│   └── ...
└── server/              # FastAPI 백엔드
    ├── main.py
    ├── tasks.py
    ├── config.py
    ├── requirements.txt
    ├── Dockerfile
    ├── .env              (생성 필요)
    └── venv/
```

---

## 🚀 설치 및 개발 환경 설정

### 사전 준비 사항

로컬 개발을 위해 다음 소프트웨어가 필요합니다:

- Git  
- Node.js (v18 이상) 및 npm  
- Python (v3.11 이상)  
- (Windows 사용자) WSL2 및 Ubuntu  
- Docker (Redis 실행 시 사용)

---

### 1. 프로젝트 클론

```
git clone https://github.com/Netnok/record-ai-agent.git
cd record-ai-agent
```

---

### 2. 백엔드 설정 (`server/`)

```
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. 프론트엔드 설정 (`client/`)

```
cd client
npm install
```

---

## 🔑 환경 변수 설정

각 디렉토리에 `.env` 파일을 생성합니다.

### server/.env

```
# OpenAI API 키
OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# GCS 설정
GCS_BUCKET_NAME="your-actual-gcs-bucket-name"
GOOGLE_APPLICATION_CREDENTIALS="/mnt/c/path/to/your/gcp-service-account-key.json"

# Redis 설정
REDIS_HOST="localhost"
REDIS_PORT="6379"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"
REDIS_DB_FOR_RESULTS="2"
REDIS_RESULT_EXPIRE_SECONDS="3600"

# STT 및 요약 설정
STT_LANGUAGE_CODE="ko"
SUMMARY_MODEL="gpt-3.5-turbo"
SUMMARY_PROMPT="You are an assistant who summarizes the given text concisely into key points in Korean."
```

※ `.env` 자동 로드를 위해 `python-dotenv` 설치 후 `config.py`에 아래 코드 추가:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

### client/.env.development

```
VITE_API_BASE_URL=http://localhost:8000
```

※ 수정 후 React 개발 서버를 재시작해야 적용됩니다.

---

## ▶️ 로컬 개발 서버 실행

총 3~4개의 터미널을 사용합니다.

---

### 터미널 1: Redis 실행

```
sudo service redis-server start
```

---

### 터미널 2: Celery 워커 실행

```
cd server/
source venv/bin/activate

# 환경 변수 설정
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="/mnt/c/.../your-key.json"

# Celery 워커 시작
celery -A tasks.celery_app worker -l info
```

---

### 터미널 3: FastAPI 서버 실행

```
cd server/
source venv/bin/activate

# 환경 변수 설정
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="/mnt/c/.../your-key.json"

# FastAPI 서버 시작
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### 터미널 4: 프론트엔드 실행

```
cd client/
npm run dev
```

접속 주소: http://localhost:3000

---

## ☁️ 배포 개요 (Google Cloud)

### 백엔드

1. `server/Dockerfile`로 이미지 빌드  
2. Google Artifact Registry에 푸시  
3. Redis: GCP Memorystore 인스턴스 생성  
4. Celery 워커: GCE VM에 배포, Systemd로 등록  
5. VPC 구성: Cloud Run, VM, Redis 간 통신 가능하도록 설정  
6. Cloud Run에 배포, 환경 변수 및 VPC 커넥터 설정

### 프론트엔드

- `npm run build`로 정적 파일 생성  
- Netlify, Vercel, 또는 GCS 웹 호스팅으로 배포

---

## 📌 참고

이 문서는 프로젝트를 처음 접하는 개발자도 빠르게 이해하고 실행할 수 있도록 작성되었습니다.  
버그 제보 및 기능 제안은 Issues 탭을 이용해주세요.
