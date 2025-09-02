#!/usr/bin/env python3
"""
DX-Safety 통합 테스트 실행 스크립트

이 스크립트는 프로젝트의 모든 테스트를 실행하고 결과를 요약합니다.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """모든 테스트 실행"""
    print("🧪 DX-Safety 통합 테스트 시작")
    print("=" * 50)
    
    # 프로젝트 루트로 이동
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 테스트 실행 명령어들
    test_commands = [
        # 기본 단위 테스트들
        ["python", "-m", "pytest", "tests/test_phase1.py", "-v"],
        ["python", "-m", "pytest", "tests/test_phase2.py", "-v"],
        ["python", "-m", "pytest", "tests/test_phase3.py", "-v"],
        ["python", "-m", "pytest", "tests/test_phase4.py", "-v"],
        ["python", "-m", "pytest", "tests/test_phase5.py", "-v"],
        
        # 통합 테스트
        ["python", "-m", "pytest", "tests/test_comprehensive.py", "-v"],
        
        # 특수 테스트들
        ["python", "-m", "pytest", "tests/test_idem_sqlite.py", "-v"],
        ["python", "-m", "pytest", "tests/test_phase1_integration.py", "-v"],
    ]
    
    results = []
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n📋 테스트 {i}/{len(test_commands)}: {' '.join(cmd[2:])}")
        print("-" * 40)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            results.append({
                'command': cmd,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            if result.returncode == 0:
                print("✅ 성공")
                # 마지막 몇 줄만 출력
                lines = result.stdout.strip().split('\n')
                for line in lines[-3:]:
                    if line.strip():
                        print(f"   {line}")
            else:
                print("❌ 실패")
                if result.stderr:
                    print(f"   오류: {result.stderr.strip()}")
                    
        except subprocess.TimeoutExpired:
            print("⏰ 시간 초과")
            results.append({
                'command': cmd,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Timeout'
            })
        except Exception as e:
            print(f"💥 예외 발생: {e}")
            results.append({
                'command': cmd,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            })
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    passed = sum(1 for r in results if r['returncode'] == 0)
    failed = len(results) - passed
    
    print(f"✅ 성공: {passed}")
    print(f"❌ 실패: {failed}")
    print(f"📈 성공률: {passed/len(results)*100:.1f}%")
    
    if failed > 0:
        print("\n🔍 실패한 테스트:")
        for i, result in enumerate(results):
            if result['returncode'] != 0:
                test_name = ' '.join(result['command'][2:])
                print(f"   - {test_name}")
    
    return passed == len(results)

def run_specific_test(test_file):
    """특정 테스트 파일 실행"""
    print(f"🎯 특정 테스트 실행: {test_file}")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    cmd = ["python", "-m", "pytest", f"tests/{test_file}", "-v"]
    
    try:
        result = subprocess.run(cmd, timeout=60)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ 시간 초과")
        return False
    except Exception as e:
        print(f"💥 예외 발생: {e}")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        # 특정 테스트 실행
        test_file = sys.argv[1]
        success = run_specific_test(test_file)
    else:
        # 모든 테스트 실행
        success = run_tests()
    
    if success:
        print("\n🎉 모든 테스트가 성공했습니다!")
        sys.exit(0)
    else:
        print("\n💔 일부 테스트가 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()
