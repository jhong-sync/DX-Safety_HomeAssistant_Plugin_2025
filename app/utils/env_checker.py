import os
from app.observability.logger import get_logger

log = get_logger()

def check_ha_environment():
    """Home Assistant 환경에서 자동 설정되는 환경 변수들을 확인합니다."""
    env_info = {
        "is_ha_addon": False,
        "supervisor_token": False,
        "mqtt_username": False,
        "mqtt_password": False,
        "ha_options_path": False
    }
    
    # Home Assistant Add-on 환경인지 확인
    if os.getenv("SUPERVISOR_TOKEN"):
        env_info["is_ha_addon"] = True
        env_info["supervisor_token"] = True
        log.info("✅ Home Assistant Add-on 환경이 감지되었습니다")
    else:
        log.info("ℹ️  일반 Python 환경에서 실행 중입니다")
    
    # MQTT 관련 환경 변수 확인
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    
    if mqtt_username:
        env_info["mqtt_username"] = True
        log.info(f"✅ MQTT 사용자명이 설정되었습니다: {mqtt_username}")
    else:
        log.info("ℹ️  MQTT 사용자명이 설정되지 않았습니다 (기본값: addons 사용)")
    
    if mqtt_password:
        env_info["mqtt_password"] = True
        log.info("✅ MQTT 비밀번호가 설정되었습니다")
    else:
        log.info("ℹ️  MQTT 비밀번호가 설정되지 않았습니다")
    
    # HA_OPTIONS_PATH 확인
    ha_options_path = os.getenv("HA_OPTIONS_PATH", "/data/options.json")
    if os.path.exists(ha_options_path):
        env_info["ha_options_path"] = True
        log.info(f"✅ 설정 파일이 존재합니다: {ha_options_path}")
    else:
        log.warning(f"⚠️  설정 파일이 존재하지 않습니다: {ha_options_path}")
    
    return env_info

def log_environment_summary():
    """환경 정보를 요약하여 로그로 출력합니다."""
    env_info = check_ha_environment()
    
    log.info("=" * 50)
    log.info("환경 설정 요약")
    log.info("=" * 50)
    
    if env_info["is_ha_addon"]:
        log.info("🏠 Home Assistant Add-on 환경")
        log.info("   - Supervisor 토큰: ✅ 사용 가능")
    else:
        log.info("💻 일반 Python 환경")
        log.info("   - Supervisor 토큰: ❌ 사용 불가")
    
    log.info(f"   - MQTT 사용자명: {'✅' if env_info['mqtt_username'] else 'ℹ️'}")
    log.info(f"   - MQTT 비밀번호: {'✅' if env_info['mqtt_password'] else 'ℹ️'}")
    log.info(f"   - 설정 파일: {'✅' if env_info['ha_options_path'] else '⚠️'}")
    
    log.info("=" * 50)
    
    return env_info
