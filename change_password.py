import re
import subprocess
import os

os.chdir(r"c:\Users\bwj10\OneDrive\바탕 화면\AI_Agents\다니 디자인 에이전트\살림 Botaem 홈페이지 프로젝트")

print("=" * 45)
print("  살림 Botaem 비밀번호 변경 도구")
print("=" * 45)
print()

# 현재 비밀번호 읽기
try:
    with open("lock.html", "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'CORRECT_PW = "([^"]+)"', content)
    current_pw = match.group(1) if match else "알 수 없음"
    print(f"  현재 비밀번호: {current_pw}")
except Exception as e:
    print(f"  오류: {e}")
    input("엔터를 눌러 종료...")
    exit()

print()
new_pw = input("  새 비밀번호 입력 (숫자 6자리 권장): ").strip()

if not new_pw:
    print("  비밀번호를 입력하지 않았습니다.")
    input("엔터를 눌러 종료...")
    exit()

print()
print("  [1/3] lock.html 비밀번호 변경 중...")
content = re.sub(r'CORRECT_PW = "[^"]+"', f'CORRECT_PW = "{new_pw}"', content)
with open("lock.html", "w", encoding="utf-8") as f:
    f.write(content)
print("        완료!")

print("  [2/3] Git 저장 중...")
subprocess.run(["git", "add", "lock.html"], check=True)
subprocess.run(["git", "commit", "-m", f"비밀번호 변경"], check=True)

print("  [3/3] 사이트 배포 중...")
subprocess.run(["git", "push", "origin", "main"], check=True)

print()
print("=" * 45)
print(f"  완료! 새 비밀번호: {new_pw}")
print("  30초 후 사이트에 자동 반영됩니다.")
print("=" * 45)
print()
input("  엔터를 눌러 창을 닫으세요...")
