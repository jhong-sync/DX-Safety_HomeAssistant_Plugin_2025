# DX-Safety CAP Ingestor

Home Assistant Add-on으로 동작하는 CAP 기반 재난 경보 수신/정규화/정책결정/디스패치 서비스입니다.

## 주요 기능
- CAP 메시지 수신: MQTT를 통한 재난 경보 수신
- 자동 정규화: 다양한 CAP 포맷을 CAE 스키마로 변환/검증
- 정책 기반 결정: 임계값/영역 규칙에 따른 알림 트리거
- Home Assistant 연동: 센서 상태 업데이트 및 이벤트 발행
- 관측성: 헬스 체크와 메트릭 제공(프로메테우스 형식)
- 테스트 유틸: 샘플 알림 발행(HA 이벤트 또는 HTTP 엔드포인트)

## 노출 센서
- `sensor.dxsafety_last_headline` — 마지막 알림 헤드라인
- `sensor.dxsafety_last_level` — 마지막 알림 레벨 (minor/moderate/severe/critical)
- `sensor.dxsafety_last_intensity` — 마지막 알림 강도
- `sensor.dxsafety_last_shelter` — 마지막 대피소 이름

## 테스트 알림

1) Home Assistant 이벤트 발행

Developer Tools > Services에서 아래 서비스/데이터를 호출합니다.

```yaml
service: homeassistant.fire_event
data:
  event_type: dxsafety_alert
  event_data:
    headline: "테스트 경보"
    description: "이것은 테스트 알림입니다"
    intensity_value: "moderate"
    level: "moderate"
    shelter: { name: "테스트 대피소" }
    links: ["https://example.com/test"]
```

2) 애드온 HTTP 엔드포인트 (Ingress 경로 하위)

POST `http://<addon-ingress-host>/trigger_test` 를 호출하면 내부적으로 `dxsafety_alert` 이벤트를 발행합니다.

## Helpers 기반 정책 조정(예시)

```yaml
# 설정 > 기기 & 서비스 > Helpers
input_number:
  dxsafety_threshold_minor: 0
  dxsafety_threshold_moderate: 1
  dxsafety_threshold_severe: 2
  dxsafety_threshold_critical: 3

input_select:
  dxsafety_light_severe_color:
    name: "Severe 경보 색상"
    options: ["red", "orange", "yellow"]
    initial: "red"
  dxsafety_light_critical_color:
    name: "Critical 경보 색상"
    options: ["red", "orange", "yellow"]
    initial: "red"

input_text:
  dxsafety_sound_profile_ios:
    name: "iOS 사운드 프로파일"
    initial: "default"
  dxsafety_channel_android:
    name: "Android 알림 채널"
    initial: "default"
```

## Lovelace 커스텀 카드

### 빌드

```bash
cd dxsafety-card
npm install
npm run build
```

빌드된 `dist/dxsafety-card.js`를 Home Assistant의 `/config/www/dxsafety-card/`로 복사합니다.

```yaml
# configuration.yaml
lovelace:
  resources:
    - url: /local/dxsafety-card/dxsafety-card.js
      type: module
```

Lovelace 대시보드에서 다음 카드를 추가합니다.

```yaml
type: custom:dxsafety-card
```

## 아키텍처 개요

```
MQTT Ingestor -> Normalizer -> Policy Engine -> Dispatcher
      |             |             |              |
   Raw CAP      CAE Schema     Decision     Home Assistant/MQTT/TTS
```

주요 컴포넌트
- `app/ingestion/mqtt_ingestor.py`: MQTT 메시지 수신
- `app/normalize/normalizer.py`: CAP -> CAE 변환 및 스키마 검증
- `app/policy/engine.py`: 정책 기반 결정
- `app/dispatch/ha_client.py`: Home Assistant API 연동
- `app/dispatch/mqtt_publisher.py`: 로컬 MQTT 발행
- `app/dispatch/tts.py`: TTS 알림 발송

## 설정

`config.yaml`의 기본 옵션은 다음과 같습니다.

```yaml
options:
  remote_mqtt:
    host: "broker.example.com"
    port: 1883
    topic: "pws/cap/#"
    qos: 1
    security_mode: "none"   # none | tls | mtls

  local_mqtt:
    host: "core-mosquitto"
    port: 1883
    topic_prefix: "dxsafety"

  policy:
    default_location: "zone.home"
    severity_threshold: "moderate"

  observability:
    http_port: 8099
    metrics_enabled: true
```

환경변수
- `SUPERVISOR_TOKEN`: Home Assistant API 접근 토큰(자동 주입)
- `HA_OPTIONS_PATH`: 옵션 파일 경로(기본 `/data/options.json`)
- `MQTT_USERNAME`: Local MQTT 사용자명(기본값: "addons")
- `MQTT_PASSWORD`: Local MQTT 비밀번호(Home Assistant 환경에서 자동 설정)

**자동 설정 기능:**
- Home Assistant Add-on 환경에서 실행 시 MQTT 연결 정보가 자동으로 설정됩니다
- `localhost` → `core-mosquitto`로 자동 변환
- 빈 사용자명/비밀번호 → Home Assistant 기본 MQTT 계정으로 자동 설정

## 모니터링

헬스: `http://<addon-ingress-host>/health`
메트릭: `http://<addon-ingress-host>/metrics`

## 배포

Home Assistant Supervisor에서 리포지토리를 추가하고 애드온을 설치한 뒤 옵션을 구성합니다.

## 문제 해결

1) 센서가 업데이트되지 않음
- `SUPERVISOR_TOKEN` 확인
- Home Assistant API 연결 상태 확인

2) 커스텀 카드 로드 실패
- 파일 경로 및 lovelace 리소스 등록 확인

## 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push the branch
5. Create a Pull Request

