# 🎧 Record-AI-Agent

AI Agent가 수업 내용을 **녹음 기반 스크립트**로 분석하고 이해를 돕는 웹 애플리케이션입니다.

> React + TypeScript + Vite + Tailwind 기반  
> 누구나 쉽게 실행하고, 기여할 수 있도록 설계된 오픈소스 프로젝트입니다.

---

## 🚀 빠른 시작

```bash
git clone https://github.com/your-org/record-ai-agent.git
cd record-ai-agent
npm install
npm dev
````

`.env` 파일을 만들어 아래 내용을 추가해주세요:

```env
VITE_OPENAI_API_KEY=your_openai_key_here
```

---

## 🖼️ 주요 기능

* 수업을 웹에서 **녹음**
* 녹음된 오디오 → **텍스트 스크립트화**
* 스크립트 기반으로 AI가 **요약 / 설명 / 질의응답**
* 이해를 돕는 결과물을 사용자에게 **UI로 표시**

---

## 🔧 기술 스택

* React, TypeScript, Vite
* TailwindCSS
* MediaRecorder API

---

## 📂 프로젝트 구조

```
src/
├── app/        # 앱 초기 설정 및 진입점
├── shared/     # 재사용 가능한 공통 자산 (UI, hooks, 유틸 등)
├── entities/   # 도메인 중심 로직 (녹음, 스크립트 등)
├── features/   # 사용자 기능 단위 모듈
├── widgets/    # 여러 기능을 조합한 UI 블록
├── pages/      # 라우트 단위의 화면 구성
├── processes/  # 주요 비즈니스 시나리오 흐름(복잡한 경우에만)
└── main.tsx    # 앱 진입점
```

---

## 🙌 기여하기

* 👉 [기여 가이드 보기](CONTRIBUTING.md)
* 🎨 [코드 스타일 가이드 보기](CODE_STYLE.md)

이 외에도 PR, 이슈, 문서 개선 등 다양한 방식의 기여를 환영합니다!

---

## 📝 라이선스

MIT License