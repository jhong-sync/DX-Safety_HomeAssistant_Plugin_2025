#!/usr/bin/env python3
"""
DX-Safety 테스트 실행 스크립트

이 스크립트는 다양한 테스트 시나리오를 실행합니다.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """명령어 실행"""
    print(f"\n{'='*60}")
    print(f"실행 중: {description}")
    print(f"명령어: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("성공")
        if result.stdout:
            print(result.stdout)
    else:
        print("실패")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="DX-Safety 테스트 실행")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all", "core", "orchestrators", "adapters", "ports", "observability", "features", "common"],
        default="all",
        help="실행할 테스트 유형"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="코드 커버리지 포함"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="상세 출력"
    )
    parser.add_argument(
        "--parallel", 
        action="store_true",
        help="병렬 실행"
    )
    
    args = parser.parse_args()
    
    # 프로젝트 루트 디렉토리로 이동
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 기본 pytest 옵션
    pytest_opts = []
    
    if args.verbose:
        pytest_opts.append("-v")
    
    if args.coverage:
        pytest_opts.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    if args.parallel:
        pytest_opts.extend(["-n", "auto"])
    
    # 테스트 타입별 실행
    success = True
    
    if args.type == "all":
        # 전체 테스트 실행
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/"
        success &= run_command(cmd, "전체 테스트 실행")
        
    elif args.type == "unit":
        # 단위 테스트만 실행
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/"
        success &= run_command(cmd, "단위 테스트 실행")
        
    elif args.type == "integration":
        # 통합 테스트만 실행
        cmd = f"python -m pytest {' '.join(pytest_opts)} -m integration tests/"
        success &= run_command(cmd, "통합 테스트 실행")
        
    elif args.type == "core":
        # Core 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/core/"
        success &= run_command(cmd, "Core 모듈 테스트 실행")
        
    elif args.type == "orchestrators":
        # Orchestrators 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/orchestrators/"
        success &= run_command(cmd, "Orchestrators 모듈 테스트 실행")
        
    elif args.type == "adapters":
        # Adapters 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/adapters/"
        success &= run_command(cmd, "Adapters 모듈 테스트 실행")
        
    elif args.type == "ports":
        # Ports 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/ports/"
        success &= run_command(cmd, "Ports 모듈 테스트 실행")
        
    elif args.type == "observability":
        # Observability 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/observability/"
        success &= run_command(cmd, "Observability 모듈 테스트 실행")
        
    elif args.type == "features":
        # Features 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/features/"
        success &= run_command(cmd, "Features 모듈 테스트 실행")
        
    elif args.type == "common":
        # Common 모듈 테스트
        cmd = f"python -m pytest {' '.join(pytest_opts)} tests/unit/common/"
        success &= run_command(cmd, "Common 모듈 테스트 실행")
    
    # 결과 출력
    print(f"\n{'='*60}")
    if success:
        print("모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("일부 테스트가 실패했습니다.")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()