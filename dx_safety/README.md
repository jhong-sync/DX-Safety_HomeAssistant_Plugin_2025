# DX-Safety CAP Ingestor

Home Assistant Add-on으로 동작하는 CAP(CAP) 기반 재난 경보 수신/정규화/정책판정/디스패치 시스템입니다.

## 🚀 주요 기능

- **CAP 메시지 수신**: MQTT를 통한 실시간 재난 경보 수신
- **자동 정규화**: 다양한 CAP 형식을 표준 CAE 스키마로 변환
- **정책 기반 판정**: 설정 가능한 임계값과 규칙에 따른 알림 트리거
- **Home Assistant 통합**: 상태 센서 노출 및 서비스 호출
- **실시간 모니터링**: 메트릭 수집 및 헬스 체크
- **테스트 서비스**: 샘플 알림 발행으로 시스템 검증

## 📊 상태 센서

애드온은 다음 센서들을 자동으로 생성하고 업데이트합니다:

- `sensor.dxsafety_last_headline` - 마지막 알림 헤드라인
- `sensor.dxsafety_last_level` - 마지막 알림 레벨 (minor/moderate/severe/critical)
- `sensor.dxsafety_last_intensity` - 마지막 알림 강도
- `sensor.dxsafety_last_shelter` - 마지막 대피소 정보

## 🔧 테스트 서비스

### `dxsafety.send_test_alert` 서비스

샘플 재난 경보를 발행하여 시스템을 테스트할 수 있습니다.

**사용법:**
```yaml
# Developer Tools > Services에서
service: dxsafety.send_test_alert
```

**발행되는 이벤트:**
```json
{
  "event_type": "dxsafety_alert",
  "payload": {
    "headline": "테스트 재난 경보",
    "description": "이것은 테스트용 재난 경보입니다.",
    "intensity_value": "moderate",
    "level": "moderate",
    "shelter": {"name": "테스트 대피소"},
    "links": ["https://example.com/test"]
  }
}
```

## 🎛️ Helpers 기반 정책 조정

Home Assistant UI에서 다음 Helpers를 생성하여 정책을 조정할 수 있습니다:

### Input Numbers (임계값 설정)
```yaml
# 설정 > 장치 및 서비스 > Helpers > 숫자 입력
input_number:
  dxsafety_threshold_minor: 0
  dxsafety_threshold_moderate: 1
  dxsafety_threshold_severe: 2
  dxsafety_threshold_critical: 3
```

### Input Selects (알림 색상)
```yaml
# 설정 > 장치 및 서비스 > Helpers > 선택 입력
input_select:
  dxsafety_light_severe_color:
    name: "Severe 알림 색상"
    options:
      - "red"
      - "orange"
      - "yellow"
    initial: "red"
  dxsafety_light_critical_color:
    name: "Critical 알림 색상"
    options:
      - "red"
      - "orange"
      - "yellow"
    initial: "red"
```

### Input Texts (알림 설정)
```yaml
# 설정 > 장치 및 서비스 > Helpers > 텍스트 입력
input_text:
  dxsafety_sound_profile_ios:
    name: "iOS 사운드 프로필"
    initial: "default"
  dxsafety_channel_android:
    name: "Android 알림 채널"
    initial: "default"
```

## 🎨 Lovelace 대시보드

### Custom Card 설치

1. **빌드 실행:**
```bash
cd lovelace/dxsafety-card
npm install
npm run build
```

2. **파일 복사:**
빌드된 `dxsafety-card.js`를 `/config/www/dxsafety-card/`에 복사

3. **리소스 등록:**
```yaml
# configuration.yaml
lovelace:
  resources:
    - url: /local/dxsafety-card/dxsafety-card.js
      type: module
```

4. **카드 추가:**
```yaml
# Lovelace 대시보드
type: custom:dxsafety-card
```

### 카드 기능

- **실시간 상태 모니터링**: 모든 DX-Safety 센서 상태 표시
- **정책 설정 관리**: Helper 값을 실시간으로 수정
- **테스트 알림**: 원클릭으로 테스트 알림 발행
- **반응형 디자인**: 모바일과 데스크톱 모두 지원

## 🏗️ 아키텍처

```
MQTT Ingestor → Normalizer → Policy Engine → Dispatcher
     ↓              ↓           ↓           ↓
  Raw CAP → CAE Schema → Decision → Home Assistant
```

### 주요 컴포넌트

- **`app/ingestion/mqtt_ingestor.py`**: MQTT 메시지 수신
- **`app/normalize/normalizer.py`**: CAP → CAE 변환
- **`app/policy/engine.py`**: 정책 기반 판정
- **`app/dispatch/ha_client.py`**: Home Assistant API 통신
- **`app/dispatch/mqtt_publisher.py`**: 로컬 MQTT 발행
- **`app/dispatch/tts.py`**: TTS 알림 발송

## ⚙️ 설정

### 기본 설정 (config.yaml)

```yaml
options:
  remote_mqtt:
    host: "broker.example.com"
    port: 8883
    topic: "pws/cap/#"
    tls: true
  
  local_mqtt:
    host: "core-mosquitto"
    port: 1883
    topic_prefix: "dxsafety"
  
  policy:
    default_location: "zone.home"
    severity_threshold: "moderate"
    radius_km_buffer: 0
  
  observability:
    http_port: 8099
    metrics_enabled: true
```

### 환경 변수

- `SUPERVISOR_TOKEN`: Home Assistant API 접근 토큰 (자동 설정)

## 📈 모니터링

### 메트릭

- `dxsafety_alerts_received_total`: 수신된 알림 수
- `dxsafety_alerts_triggered_total`: 트리거된 알림 수

### 헬스 체크

- HTTP 엔드포인트: `http://localhost:8099/health`
- 메트릭 엔드포인트: `http://localhost:8099/metrics`

## 🚀 설치 및 실행

### 1. Add-on 설치

Home Assistant Supervisor에서 이 저장소를 추가하고 설치

### 2. 설정 구성

Add-on 설정에서 MQTT 브로커 정보와 정책 설정

### 3. Helpers 생성

위의 Helpers 섹션을 참고하여 필요한 엔티티 생성

### 4. 대시보드 설정

Lovelace에 custom card 추가하여 모니터링

## 🔍 문제 해결

### 일반적인 문제

1. **센서가 업데이트되지 않음**
   - `SUPERVISOR_TOKEN` 확인
   - Home Assistant API 연결 상태 점검

2. **테스트 서비스 호출 실패**
   - Add-on 로그 확인
   - 서비스 권한 확인

3. **Custom Card 로드 실패**
   - 파일 경로 확인
   - 리소스 등록 상태 확인

### 로그 확인

```bash
# Add-on 로그
docker logs addon_dx_safety_cap
```

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면 GitHub Issues를 통해 문의해 주세요.
