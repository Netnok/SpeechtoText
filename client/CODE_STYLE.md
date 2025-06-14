# 🧑‍🎨 코드 스타일 가이드 (React + TypeScript)

이 프로젝트는 **가독성**, **재사용성**, **유지보수성**을 중요시합니다.  
아래 가이드를 참고해 주세요.

---

## 📁 디렉토리 구조

```
src/
├── app/        # 앱 초기 설정 및 진입점
├── shared/     # 재사용 가능한 공통 자산 (UI, hooks, 유틸 등)
├── features/   # 사용자 기능 단위 모듈
├── pages/      # 라우트 단위의 화면 구성
└── main.tsx    # 앱 진입점
```
---

## 🧾 타입 정의

- `Props` 타입은 명시적으로 정의 (추론 X)
- 공통 타입은 `types/`에 정의
- 유니온/제네릭 적극 활용

```ts
type RecordingStatus = 'idle' | 'recording' | 'processing';

interface AudioSegment {
  id: string;
  blob: Blob;
  duration: number;
}
````

---

## 🎯 컴포넌트

* 역할 분리: `Presentational vs Container` 컴포넌트
* 가능한 경우 `useMemo`, `useCallback` 사용해 최적화
* 상태 최소화, 상위와 결합 최소화

---

## 💅 스타일링 (Tailwind)

* `className`은 줄 개행으로 관리
* 중복 스타일 추상화는 `clsx`, `classnames`로 추후 적용 예정
* 전역적인 디자인 토큰은 추후 `tailwind.config.ts` 확장 예정

```tsx
<button
  className="
    px-4 py-2
    rounded-xl
    text-white
    bg-blue-500
    hover:bg-blue-600
  "
>
  전송
</button>
```

---

## 🧪 테스트 (Optional)

* 단위 테스트는 `vitest` + `testing-library/react` 적용 예정
* 비즈니스 로직은 UI와 분리해 테스트 가능 구조로 작성

---

앞으로 코드 스타일은 팀 내 논의를 통해 지속적으로 개선될 예정입니다.
기여 전 이 가이드를 꼭 읽어주세요 🙏
