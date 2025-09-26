# DX-Safety 테스트 가이드

## 📋 테스트 구조

```
tests/
├── conftest.py                 # 테스트 설정 및 픽스처
├── test_plan.md               # 테스트 계획서
└── unit/                      # 단위 테스트
    ├── adapters/              # Adapter 모듈 테스트
    │   ├── test_ha_tts.py     # Home Assistant & TTS 테스트
    │   ├── test_mqtt.py       # MQTT 테스트
    │   └── test_storage.py    # Storage 테스트
    ├── common/                # Common 모듈 테스트
    │   └── test_common.py     # 지리 유틸리티 & 재시도 로직 테스트
    ├── core/                  # Core 모듈 테스트
    │   ├── test_core_geo_policy_hypothesis.py
    │   ├── test_core_models_hypothesis.py
    │   ├── test_core_normalize_hypothesis.py
    │   ├── test_core_policy_hypothesis.py
    │   └── test_core_voice_template_hypothesis.py
    ├── features/              # Features 모듈 테스트
    │   └── test_shelter_nav.py # 대피소 네비게이션 테스트
    ├── observability/         # Observability 모듈 테스트
    │   └── test_observability.py # 헬스 체크, 메트릭, 로깅 테스트
    ├── orchestrators/         # Orchestrators 모듈 테스트
    │   ├── test_orchestrator.py # 메인 오케스트레이터 테스트
    │   └── test_orchestrator_phases.py # Phase 오케스트레이터 테스트
    └── ports/                 # Ports 모듈 테스트
        └── test_ports.py      # 포트 인터페이스 테스트
```

## 🚀 테스트 실행

### 기본 실행

```bash
# 전체 테스트 실행
python run_tests.py

# 단위 테스트만 실행
python run_tests.py --type unit

# 특정 모듈 테스트
python run_tests.py --type core
python run_tests.py --type orchestrators
python run_tests.py --type adapters
python run_tests.py --type ports
python run_tests.py --type observability
python run_tests.py --type features
python run_tests.py --type common
```

### 고급 옵션

```bash
# 코드 커버리지 포함
python run_tests.py --coverage

# 상세 출력
python run_tests.py --verbose

# 병렬 실행
python run_tests.py --parallel

# 모든 옵션 조합
python run_tests.py --type unit --coverage --verbose --parallel
```

### 직접 pytest 실행

```bash
# 전체 테스트
pytest tests/

# 단위 테스트
pytest tests/unit/

# 특정 모듈
pytest tests/unit/core/
pytest tests/unit/orchestrators/
pytest tests/unit/adapters/

# 특정 테스트 파일
pytest tests/unit/core/test_core_models_hypothesis.py

# 특정 테스트 함수
pytest tests/unit/core/test_core_models_hypothesis.py::test_cae_creation

# 마커 사용
pytest -m asyncio tests/
pytest -m slow tests/
pytest -m integration tests/
```

## 📊 테스트 커버리지

```bash
# HTML 리포트 생성
pytest --cov=app --cov-report=html tests/

# 터미널 리포트
pytest --cov=app --cov-report=term tests/

# XML 리포트
pytest --cov=app --cov-report=xml tests/
```

## 🔧 테스트 설정

### pytest.ini 설정

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --durations=10
markers =
    asyncio: 비동기 테스트
    slow: 느린 테스트
    integration: 통합 테스트
    unit: 단위 테스트
    functional: 기능 테스트
    performance: 성능 테스트
    security: 보안 테스트
```

### conftest.py 픽스처

- `event_loop`: 세션 스코프의 이벤트 루프
- `temp_db_path`: 임시 데이터베이스 파일 경로
- `temp_file_path`: 임시 파일 경로
- `sample_settings`: 테스트용 설정
- `mock_ha_client`: 테스트용 Home Assistant 클라이언트
- `mock_mqtt_client`: 테스트용 MQTT 클라이언트
- `mock_tts_engine`: 테스트용 TTS 엔진
- `sample_cae`: 테스트용 CAE 객체
- `sample_decision`: 테스트용 Decision 객체
- `sample_shelters`: 테스트용 대피소 데이터
- `sample_polygon`: 테스트용 폴리곤
- `mock_dependencies`: 테스트용 의존성 목업

## 📝 테스트 작성 가이드

### 테스트 클래스 구조

```python
class TestClassName:
    """테스트 클래스 설명"""
    
    @pytest.fixture
    def sample_data(self):
        """테스트용 데이터"""
        return {"key": "value"}
    
    def test_method_name(self, sample_data):
        """테스트 메서드 설명"""
        # Given
        input_data = sample_data
        
        # When
        result = function_under_test(input_data)
        
        # Then
        assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """비동기 테스트"""
        result = await async_function()
        assert result is not None
```

### 테스트 명명 규칙

- 테스트 파일: `test_*.py`
- 테스트 클래스: `Test*`
- 테스트 메서드: `test_*`
- 픽스처: `*_fixture` 또는 `sample_*`

### 테스트 마커 사용

```python
@pytest.mark.asyncio
async def test_async_function():
    """비동기 테스트"""
    pass

@pytest.mark.slow
def test_performance():
    """성능 테스트"""
    pass

@pytest.mark.integration
def test_integration():
    """통합 테스트"""
    pass
```

## 🐛 디버깅

### 테스트 실패 시 디버깅

```bash
# 상세한 에러 정보 출력
pytest -v --tb=long tests/

# 첫 번째 실패에서 중단
pytest -x tests/

# 실패한 테스트만 재실행
pytest --lf tests/

# 특정 테스트 디버깅
pytest -s tests/unit/core/test_core_models_hypothesis.py::test_cae_creation
```

### 로그 출력

```bash
# 로그 출력 활성화
pytest -s --log-cli-level=DEBUG tests/

# 특정 로거만 출력
pytest -s --log-cli-level=DEBUG --log-cli-format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s" tests/
```

## 📈 성능 테스트

```bash
# 느린 테스트만 실행
pytest -m slow tests/

# 테스트 실행 시간 측정
pytest --durations=10 tests/

# 병렬 실행으로 성능 향상
pytest -n auto tests/
```

## 🔒 보안 테스트

```bash
# 보안 테스트만 실행
pytest -m security tests/

# 보안 관련 테스트 파일
pytest tests/unit/adapters/test_storage.py
pytest tests/unit/adapters/test_ha_tts.py
```

## 📋 테스트 체크리스트

- [ ] 모든 모듈에 대한 단위 테스트 작성
- [ ] 비동기 함수에 대한 테스트 작성
- [ ] 에러 처리 테스트 작성
- [ ] 경계값 테스트 작성
- [ ] 성능 테스트 작성
- [ ] 보안 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 코드 커버리지 80% 이상 달성
- [ ] 테스트 문서화 완료
- [ ] CI/CD 파이프라인에 테스트 통합

## 🚨 주의사항

1. **테스트 격리**: 각 테스트는 독립적으로 실행되어야 함
2. **데이터 정리**: 테스트 후 임시 파일과 데이터 정리
3. **모킹 사용**: 외부 의존성은 모킹하여 테스트
4. **비동기 테스트**: `@pytest.mark.asyncio` 마커 사용
5. **에러 처리**: 예외 상황에 대한 테스트 포함
6. **성능 고려**: 테스트 실행 시간 최적화

## 📚 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [pytest-asyncio 문서](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)
- [pytest-xdist 문서](https://pytest-xdist.readthedocs.io/)
