# DX-Safety Home Assistant Add-on

🏠 **Home Assistant용 CAP 기반 재난 경보 시스템**

DX-Safety는 Common Alerting Protocol (CAP) 기반의 재난 경보를 수신하고, 지능적으로 필터링하여 Home Assistant에서 실시간 알림을 제공하는 애드온입니다.

## 주요 기능

### 실시간 경보 수신
- **MQTT 기반 CAP 메시지 수신**: 외부 재난 경보 시스템과 실시간 연결
- **다양한 보안 모드 지원**: None, TLS, mTLS 인증 지원
- **자동 재연결**: 네트워크 불안정 시 자동 복구

### 지능형 필터링
- **지리적 정책**: 설정된 반경 내 경보만 수신
- **심각도 임계값**: minor/moderate/severe/critical 레벨별 필터링
- **중복 제거**: 동일 경보의 중복 알림 방지
- **야간 모드**: 시간대별 알림 제어

### Home Assistant 통합
- **센서 자동 생성**: 경보 정보를 실시간 센서로 제공
- **이벤트 발행**: Home Assistant 이벤트 시스템과 연동
- **자동화 트리거**: 경보 수신 시 자동화 실행
- **TTS 음성 알림**: 음성으로 경보 내용 안내

### 모니터링 & 관찰성
- **실시간 메트릭**: Prometheus 형식의 성능 지표
- **구조화된 로깅**: 상세한 운영 로그
- **헬스 체크**: 서비스 상태 모니터링
- **웹 대시보드**: Ingress를 통한 관리 인터페이스

## 설치 방법

### 1. 저장소 추가
Home Assistant 설정 → 애드온 → 애드온 스토어 → 우측 상단 메뉴 → 저장소

```
https://github.com/jhong-sync/DX-Safety_HomeAssistant_Plugin_2025
```

### 2. 애드온 설치
- **DX-Safety CAP Ingestor** 검색 후 설치
- 설치 완료 후 **시작** 버튼 클릭

### 3. 기본 설정
설치 후 자동으로 생성되는 센서들:
- `sensor.dxsafety_last_headline` - 마지막 경보 제목
- `sensor.dxsafety_last_level` - 마지막 경보 레벨
- `sensor.dxsafety_last_intensity` - 마지막 경보 강도
- `sensor.dxsafety_last_shelter` - 마지막 대피소 정보

## 설정 가이드

### 기본 설정 (config.yaml)

```yaml
# 외부 MQTT 브로커 설정
remote_mqtt:
  host: "your-mqtt-broker.com"
  port: 1883
  topic: "pws/cap/#"
  qos: 1
  security_mode: "none"  # none | tls | mtls
  username: "your-username"
  password: "your-password"

# 로컬 MQTT 설정 (Home Assistant Mosquitto)
local_mqtt:
  host: "core-mosquitto"  # 자동 설정됨
  port: 1883
  topic_prefix: "dxsafety"
  enabled: true

# 정책 설정
policy:
  default_location: "zone.home"
  lat: 37.5665  # 서울시청 좌표 (예시)
  lon: 126.9780
  radius_km_buffer: 10
  severity_threshold: "moderate"  # minor|moderate|severe|critical
  night_mode: false

# TTS 음성 알림
tts:
  enabled: true
  topic: "dxsafety/tts"
  template: "{headline} - {description}"
  voice_language: "ko-KR"

# 관찰성 설정
observability:
  http_port: 8099
  metrics_enabled: true
  log_level: "INFO"
```

### 고급 설정

#### TLS 보안 연결
```yaml
remote_mqtt:
  security_mode: "tls"
  ca_cert_path: "/ssl/ca.crt"
  username: "secure-user"
  password: "secure-password"
```

#### mTLS 상호 인증
```yaml
remote_mqtt:
  security_mode: "mtls"
  ca_cert_path: "/ssl/ca.crt"
  client_cert_path: "/ssl/client.crt"
  client_key_path: "/ssl/client.key"
```

## 자동화 예시

### 1. 경보 수신 시 조명 제어
```yaml
automation:
  - alias: "DX-Safety 경보 시 조명 켜기"
    trigger:
      platform: event
      event_type: dxsafety_alert
    condition:
      condition: template
      value_template: "{{ trigger.event.data.level in ['severe', 'critical'] }}"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          rgb_color: [255, 0, 0]  # 빨간색
          brightness: 255
```

### 2. 음성 알림 자동화
```yaml
automation:
  - alias: "DX-Safety 음성 알림"
    trigger:
      platform: event
      event_type: dxsafety_alert
    action:
      - service: tts.cloud_say
        data:
          entity_id: media_player.living_room
          message: "{{ trigger.event.data.headline }} - {{ trigger.event.data.description }}"
          language: ko
```

### 3. 대피소 정보 표시
```yaml
automation:
  - alias: "대피소 정보 알림"
    trigger:
      platform: state
      entity_id: sensor.dxsafety_last_shelter
    condition:
      condition: not
      condition: template
      value_template: "{{ states('sensor.dxsafety_last_shelter') == 'unavailable' }}"
    action:
      - service: persistent_notification.create
        data:
          title: "대피소 정보"
          message: "{{ states('sensor.dxsafety_last_shelter') }}"
```

## 테스트 방법

### 1. Home Assistant 이벤트로 테스트
개발자 도구 → 서비스에서 다음 호출:

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

### 2. HTTP 엔드포인트로 테스트
```bash
curl -X POST http://your-ha-ip:8099/trigger_test
```

## 모니터링

### 헬스 체크
```
http://your-ha-ip:8099/health
```

### 메트릭 (Prometheus)
```
http://your-ha-ip:8099/metrics
```

### 주요 메트릭
- `dxsafety_alerts_received_total` - 수신된 경보 수
- `dxsafety_alerts_processed_total` - 처리된 경보 수
- `dxsafety_queue_depth` - 처리 큐 깊이
- `dxsafety_processing_duration_seconds` - 처리 시간

## 🔍 문제 해결

### 일반적인 문제들

#### 1. 센서가 업데이트되지 않음
- Home Assistant API 토큰 확인
- 네트워크 연결 상태 확인
- 로그에서 오류 메시지 확인

#### 2. MQTT 연결 실패
- 브로커 주소 및 포트 확인
- 인증 정보 확인
- 방화벽 설정 확인

#### 3. 경보가 수신되지 않음
- 토픽 설정 확인
- QoS 레벨 확인
- 보안 설정 확인

### 로그 확인
```bash
# 애드온 로그 확인
docker logs dx_safety
```

## 아키텍처

```
외부 CAP 시스템 → MQTT → DX-Safety → Home Assistant
     ↓              ↓         ↓           ↓
  재난 경보    실시간 수신   지능형 필터링   자동화/알림
```

### 핵심 컴포넌트
- **MQTT Ingestor**: 외부 경보 시스템과 연결
- **Normalizer**: CAP 메시지를 표준 형식으로 변환
- **Policy Engine**: 지리적/심각도 기반 필터링
- **Dispatcher**: Home Assistant 센서/이벤트 업데이트
- **TTS Engine**: 음성 알림 생성

## 기여하기

1. 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/jhong-sync/DX-Safety_HomeAssistant_Plugin_2025/issues)
- **문서**: [Wiki](https://github.com/jhong-sync/DX-Safety_HomeAssistant_Plugin_2025/wiki)
- **이메일**: jahong215@synctechno.com

---

**버전**: 0.1.3  
**Home Assistant 최소 버전**: 2024.6.0  
**Python 버전**: 3.11+

