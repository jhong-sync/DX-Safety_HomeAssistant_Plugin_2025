# DX-Safety Custom Card

Home Assistant용 DX-Safety 모니터링 및 설정 관리 카드입니다.

## 기능

- 실시간 DX-Safety 센서 상태 모니터링
- 정책 임계값 설정
- 알림 설정 관리
- 테스트 알림 발행

## 빌드 방법

### 1. 의존성 설치
```bash
npm install
```

### 2. 개발 모드 실행
```bash
npm run dev
```

### 3. 프로덕션 빌드
```bash
npm run build
```

빌드된 파일은 `/config/www/dxsafety-card/` 디렉토리에 생성됩니다.

## Home Assistant 설정

### 1. Custom Card 등록
`/config/www/dxsafety-card/dxsafety-card.js` 파일을 Home Assistant의 `www` 디렉토리에 복사합니다.

### 2. Lovelace 설정
`configuration.yaml` 또는 Lovelace UI 편집기에서:

```yaml
resources:
  - url: /local/dxsafety-card/dxsafety-card.js
    type: module
```

### 3. 카드 추가
Lovelace 대시보드에 다음 코드를 추가:

```yaml
type: custom:dxsafety-card
```

## 필요한 Helpers

다음 Helpers를 Home Assistant에서 생성해야 합니다:

### Input Numbers
- `input_number.dxsafety_threshold_minor`
- `input_number.dxsafety_threshold_moderate`
- `input_number.dxsafety_threshold_severe`
- `input_number.dxsafety_threshold_critical`

### Input Selects
- `input_select.dxsafety_light_severe_color`
- `input_select.dxsafety_light_critical_color`

### Input Texts
- `input_text.dxsafety_sound_profile_ios`
- `input_text.dxsafety_channel_android`

## 기술 스택

- React 18
- TypeScript
- Tailwind CSS
- Vite
