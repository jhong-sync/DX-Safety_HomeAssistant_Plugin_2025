#!/usr/bin/env python3
"""
대피소 네비게이션 기능 실제 테스트 스크립트

이 스크립트는 실제 Home Assistant 환경에서 대피소 네비게이션 기능을 테스트합니다.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.settings import Settings
from app.adapters.homeassistant.client import HAClient
from app.features.shelter_nav import ShelterNavigator
from app.observability.logging_setup import get_logger

log = get_logger("dxsafety.test_shelter")

async def test_shelter_navigation():
    """대피소 네비게이션 기능을 테스트합니다."""
    
    # 설정 로드
    settings = Settings()
    
    # Home Assistant 클라이언트 생성
    ha_client = HAClient(
        base_url=settings.ha.base_url,
        token=settings.ha.token,
        timeout=settings.ha.timeout_sec
    )
    
    try:
        async with ha_client:
            log.info("Home Assistant 연결 성공")
            
            # 1. 모바일 notify 서비스 목록 확인
            mobile_services = await ha_client.list_notify_mobile_services()
            log.info(f"모바일 notify 서비스 목록: {mobile_services}")
            
            # 2. 위치 추적 디바이스 목록 확인
            devices = await ha_client.get_device_trackers()
            log.info(f"위치 추적 디바이스 목록: {devices}")
            
            if not devices:
                log.warning("위치 추적 디바이스가 없습니다. 테스트를 종료합니다.")
                return
            
            # 3. 대피소 네비게이터 생성
            nav = ShelterNavigator(
                ha=ha_client,
                path=settings.shelter_nav.file_path,
                appname=settings.shelter_nav.appname
            )
            
            # 4. 대피소 데이터 로드 테스트
            try:
                nav.load()
                log.info(f"대피소 데이터 로드 성공: {len(nav._shelters)}개")
                
                # 대피소 목록 출력
                for i, shelter in enumerate(nav._shelters[:5]):  # 처음 5개만 출력
                    log.info(f"대피소 {i+1}: {shelter['name']} ({shelter['lat']}, {shelter['lon']})")
                
            except FileNotFoundError:
                log.error(f"대피소 파일을 찾을 수 없습니다: {settings.shelter_nav.file_path}")
                log.info("테스트용 대피소 데이터를 생성합니다...")
                
                # 테스트용 대피소 데이터 생성
                test_shelters = [
                    {"name": "서울시민대피소", "address": "서울특별시 중구 세종대로 110", "lat": 37.5665, "lon": 126.9780},
                    {"name": "강남구대피소", "address": "서울특별시 강남구 테헤란로 152", "lat": 37.5172, "lon": 127.0473},
                    {"name": "마포구대피소", "address": "서울특별시 마포구 와우산로 94", "lat": 37.5572, "lon": 126.9236},
                ]
                nav._shelters = test_shelters
                log.info("테스트용 대피소 데이터 설정 완료")
            
            # 5. 각 디바이스별 최근접 대피소 계산 테스트
            for device in devices:
                try:
                    from app.features.shelter_nav import find_nearest, build_naver_url
                    
                    nearest, distance = find_nearest(device["lat"], device["lon"], nav._shelters)
                    url = build_naver_url(
                        float(nearest["lat"]), 
                        float(nearest["lon"]),
                        str(nearest["name"]), 
                        nav.appname
                    )
                    
                    log.info(f"디바이스: {device['name']}")
                    log.info(f"  위치: ({device['lat']}, {device['lon']})")
                    log.info(f"  최근접 대피소: {nearest['name']}")
                    log.info(f"  거리: {distance:.2f}km")
                    log.info(f"  네이버 지도 URL: {url}")
                    log.info("")
                    
                except Exception as e:
                    log.error(f"디바이스 {device['name']} 처리 중 오류: {e}")
            
            # 6. 실제 알림 발송 테스트 (선택사항)
            if mobile_services:
                log.info("실제 알림 발송을 테스트합니다...")
                try:
                    await nav.notify_all_devices()
                    log.info("알림 발송 테스트 완료")
                except Exception as e:
                    log.error(f"알림 발송 테스트 실패: {e}")
            else:
                log.warning("모바일 notify 서비스가 없어서 알림 발송 테스트를 건너뜁니다.")
    
    except Exception as e:
        log.error(f"테스트 중 오류 발생: {e}")
        raise

async def test_api_endpoint():
    """API 엔드포인트를 테스트합니다."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            # 헬스 체크
            response = await client.get("http://localhost:8099/health")
            log.info(f"헬스 체크 응답: {response.status_code}")
            
            # 대피소 알림 엔드포인트 테스트
            response = await client.post(
                "http://localhost:8099/shelter/notify",
                json={"notify_group": ""}
            )
            log.info(f"대피소 알림 API 응답: {response.status_code}")
            if response.status_code == 200:
                log.info(f"응답 내용: {response.json()}")
    
    except Exception as e:
        log.error(f"API 테스트 중 오류: {e}")

def main():
    """메인 함수"""
    log.info("대피소 네비게이션 기능 테스트 시작")
    
    # 테스트 실행
    asyncio.run(test_shelter_navigation())
    
    # API 엔드포인트 테스트 (서버가 실행 중일 때만)
    try:
        asyncio.run(test_api_endpoint())
    except Exception as e:
        log.warning(f"API 엔드포인트 테스트 건너뜀: {e}")
    
    log.info("대피소 네비게이션 기능 테스트 완료")

if __name__ == "__main__":
    main()
