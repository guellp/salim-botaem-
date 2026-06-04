@echo off
chcp 65001 > nul
cd /d "c:\Users\bwj10\OneDrive\바탕 화면\AI_Agents\다니 디자인 에이전트\살림 Botaem 홈페이지 프로젝트"

echo.
echo ========================================
echo   살림 Botaem 비밀번호 변경 도구
echo ========================================
echo.

:: 현재 비밀번호 읽기
for /f "tokens=*" %%i in ('python -c "
import re
with open(\"lock.html\", \"r\", encoding=\"utf-8\") as f:
    content = f.read()
match = re.search(r'CORRECT_PW = \"(\d+)\"', content)
print(match.group(1) if match else \"알 수 없음\")
"') do set CURRENT_PW=%%i

echo  현재 비밀번호: %CURRENT_PW%
echo.
set /p NEW_PW= 새 비밀번호 입력 (숫자 6자리 권장): 

if "%NEW_PW%"=="" (
    echo 비밀번호를 입력하지 않았습니다. 종료합니다.
    pause
    exit /b
)

echo.
echo  [1/3] lock.html 비밀번호 변경 중...

python -c "
import re
new_pw = '%NEW_PW%'
with open('lock.html', 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'CORRECT_PW = \"\d+\"', f'CORRECT_PW = \"{new_pw}\"', content)
with open('lock.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('  완료!')
"

echo  [2/3] Git 저장 중...
git add lock.html
git commit -m "비밀번호 변경: %NEW_PW%"

echo  [3/3] 사이트 배포 중...
git push origin main

echo.
echo ========================================
echo  ✅ 완료! 새 비밀번호: %NEW_PW%
echo  약 30초 후 사이트에 반영됩니다.
echo ========================================
echo.
pause
