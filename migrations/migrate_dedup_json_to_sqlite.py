"""
JSON 기반 dedup 파일을 SQLite로 마이그레이션하는 스크립트.

기존 DedupStore의 JSON 파일을 SQLiteIdemStore로 안전하게 변환하여
데이터 무결성을 보장합니다.
"""

import json
import sys
import asyncio
import time
from pathlib import Path
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.observability.logger import get_logger

log = get_logger()


async def migrate(json_path: str, sqlite_path: str, ttl_sec: int = 86400):
    """
    JSON dedup 파일을 SQLite로 마이그레이션합니다.
    
    Args:
        json_path: JSON dedup 파일 경로
        sqlite_path: SQLite 데이터베이스 파일 경로
        ttl_sec: TTL 만료 시간 (초)
    """
    # JSON 파일 존재 확인
    json_file = Path(json_path)
    if not json_file.exists():
        log.error(f"JSON 파일이 존재하지 않습니다: {json_path}")
        return False
    
    # SQLiteIdemStore 초기화
    store = SQLiteIdemStore(sqlite_path, ttl_sec)
    await store.init()
    
    # JSON 파일 읽기 및 파싱
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"JSON 파일 로드 완료: {json_path}, 항목 수: {len(data)}")
    except Exception as e:
        log.error(f"JSON 파일 읽기 실패: {e}")
        return False
    
    # 현재 시간 기준으로 만료된 항목 필터링
    now = int(time.time())
    valid_data = {k: v for k, v in data.items() if now - v < ttl_sec}
    expired_count = len(data) - len(valid_data)
    
    if expired_count > 0:
        log.info(f"만료된 항목 {expired_count}개 제외됨")
    
    # 데이터 마이그레이션
    count = 0
    skipped = 0
    errors = 0
    
    for key, timestamp in valid_data.items():
        try:
            # SQLiteIdemStore는 키가 이미 존재하면 False를 반환
            ok = await store.add_if_absent(key)
            if ok:
                count += 1
            else:
                skipped += 1
        except Exception as e:
            log.error(f"키 '{key}' 마이그레이션 실패: {e}")
            errors += 1
    
    # 마이그레이션 결과 보고
    log.info(f"마이그레이션 완료:")
    log.info(f"  - 성공: {count}개")
    log.info(f"  - 건너뜀 (이미 존재): {skipped}개")
    log.info(f"  - 에러: {errors}개")
    log.info(f"  - 만료됨: {expired_count}개")
    log.info(f"  - 대상 SQLite 파일: {sqlite_path}")
    
    # 최종 검증
    final_count = await store.get_count()
    log.info(f"SQLite 저장소 최종 항목 수: {final_count}")
    
    return errors == 0


async def main():
    """메인 함수"""
    if len(sys.argv) < 3:
        print("사용법: python migrate_dedup_json_to_sqlite.py <json_file> <sqlite_file> [ttl_seconds]")
        print("예시: python migrate_dedup_json_to_sqlite.py /data/dedup.json /data/idem.db 86400")
        sys.exit(1)
    
    json_path = sys.argv[1]
    sqlite_path = sys.argv[2]
    ttl_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 86400
    
    print(f"마이그레이션 시작:")
    print(f"  - JSON 파일: {json_path}")
    print(f"  - SQLite 파일: {sqlite_path}")
    print(f"  - TTL: {ttl_sec}초")
    print()
    
    try:
        success = await migrate(json_path, sqlite_path, ttl_sec)
        if success:
            print("마이그레이션이 성공적으로 완료되었습니다.")
            sys.exit(0)
        else:
            print("마이그레이션 중 오류가 발생했습니다.")
            sys.exit(1)
    except Exception as e:
        print(f"마이그레이션 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

