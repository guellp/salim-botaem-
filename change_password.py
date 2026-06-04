# -*- coding: utf-8 -*-
import subprocess
import os
import sys

# UTF-8 출력 보정
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

os.chdir(r"c:\Users\bwj10\OneDrive\바탕 화면\AI_Agents\다니 디자인 에이전트\살림 Botaem 홈페이지 프로젝트")

print("=" * 45)
print("  살림 Botaem 비밀번호 변경 도구")
print("=" * 45)
print()

# 현재 비밀번호 읽기
current_pw = "알 수 없음"
if os.path.exists("password.txt"):
    try:
        with open("password.txt", "r", encoding="utf-8") as f:
            current_pw = f.read().strip()
    except:
        pass

if current_pw == "알 수 없음":
    try:
        with open("lock.html", "r", encoding="utf-8") as f:
            content = f.read()
        import re
        match = re.search(r'CORRECT_PW = "([^"]+)"', content)
        current_pw = match.group(1) if match else "알 수 없음"
    except:
        pass

print(f"  현재 비밀번호: {current_pw}")
print()
new_pw = input("  새 비밀번호 입력 (숫자 6자리 권장): ").strip()

if not new_pw:
    print("  비밀번호를 입력하지 않았습니다.")
    input("엔터를 눌러 종료...")
    exit()

if len(new_pw) != 6 or not new_pw.isdigit():
    print("  ⚠️ 주의: 비밀번호는 숫자 6자리를 입력하셔야 정상 작동합니다.")
    input("엔터를 눌러 종료...")
    exit()

print()
print("  [1/2] password.txt 비밀번호 기록 중...")
with open("password.txt", "w", encoding="utf-8") as f:
    f.write(new_pw)
print("        완료!")

print("  [2/2] 인젝터 호출 및 전체 동기화 실행 중...")
print("        (데이터 최신화 + 비밀번호 일괄 주입 및 깃허브 업로드)")
print("-" * 45)
try:
    result = subprocess.run(["python", "inject_sheet_data.py"], check=True, capture_output=True, text=True, encoding="utf-8")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(f"\n  ❌ 동기화 중 오류 발생: {e}")
    print(e.stdout)
    print(e.stderr)
    input("엔터를 눌러 종료...")
    exit()

print("-" * 45)
print()
print("=" * 45)
print(f"  🎉 완료! 새 비밀번호: {new_pw}")
print("  약 30초 후 사이트에 자동 반영됩니다.")
print("=" * 45)
print()
input("  엔터를 눌러 창을 닫으세요...")
