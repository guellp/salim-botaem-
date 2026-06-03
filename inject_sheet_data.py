# -*- coding: utf-8 -*-
"""
🚀 안토부장 구글 시트 1만 건 데이터 내장 자동화 인젝터 (inject_sheet_data.py)
- 구글 스프레드시트의 원본 CSV 데이터를 직접 긁어와서 파싱
- 정제한 데이터를 index.html의 로컬 데이터베이스 영역에 완전 주입
- 오프라인 환경에서도 CORS 차단 없이 1초 만에 로딩 완료
"""

import os
import sys
import csv
import json
import urllib.request

# UTF-8 출력 설정
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

CSV_EXPORT_URL = 'https://docs.google.com/spreadsheets/d/11hy8EhKKHcBH5q6sFM6LIycVcYkVJR6ScD6j2nOEqfw/export?format=csv'
HTML_FILE_PATH = 'index.html'

def download_and_parse_sheet():
    print(f"📥 구글 시트 데이터 다운로드 중... ({CSV_EXPORT_URL})")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        req = urllib.request.Request(CSV_EXPORT_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode('utf-8')
            
        print("   🏆 데이터 다운로드 완료! CSV 데이터 파싱 개시...")
        
        # CSV 파싱
        reader = csv.DictReader(content.splitlines())
        
        # 요구된 11개 필드 명세 매핑
        required_headers = [
            "시도", "구군", "서비스명", "소관기관명", "서비스분야", 
            "지원구분", "신청기한", "지원내용", "지원대상", "신청방법", "정보수정일"
        ]
        
        parsed_records = []
        for row in reader:
            record = {}
            for h in required_headers:
                val = ""
                if h == "시도":
                    val = row.get("지역(도/시)", row.get("시도", ""))
                elif h == "구군":
                    val = row.get("지역(시/군/구)", row.get("구군", ""))
                else:
                    val = row.get(h, "")
                record[h] = val.strip() if val else ""
            
            # 최소한 '서비스명'은 존재해야 유효한 데이터로 판단
            if record["서비스명"]:
                parsed_records.append(record)
                
        print(f"   📊 파싱 성공: 총 {len(parsed_records)}건의 지원금 혜택 레코드 추출 완료!")
        return parsed_records
        
    except Exception as e:
        print(f"🚨 구글 시트 데이터 다운로드/파싱 실패: {e}")
        raise e

def inject_data_to_html(records):
    if not os.path.exists(HTML_FILE_PATH):
        raise FileNotFoundError(f"❌ 대상을 찾을 수 없습니다: {HTML_FILE_PATH}")
        
    print(f"🔄 {HTML_FILE_PATH} 파일 로드 및 내장 주입 개시...")
    
    with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 🚨 추가 패치: password.txt가 존재하면 비밀번호를 읽어서 index.html에 동적 반영 🚨
    password_file = 'password.txt'
    passcode = "123456" # 기본 패스코드
    if os.path.exists(password_file):
        try:
            with open(password_file, 'r', encoding='utf-8') as pf:
                raw_pass = pf.read().strip()
                if len(raw_pass) == 6 and raw_pass.isdigit():
                    passcode = raw_pass
                    print(f"🔑 password.txt에서 사용자 정의 비밀번호 감지: [{passcode}]")
                else:
                    print("⚠️ password.txt의 내용이 6자리 숫자가 아닙니다. 기본 비밀번호(123456)를 사용합니다.")
        except Exception as pe:
            print(f"⚠️ password.txt 읽기 실패: {pe}")
    else:
        print("💡 password.txt 파일이 존재하지 않아 기본 비밀번호(123456)를 적용합니다.")

    # HTML 내의 CORRECT_PASSCODE 값을 찾아서 치환
    import re
    # const CORRECT_PASSCODE = "xxxxxx"; 패턴 찾기
    passcode_pattern = r'(const CORRECT_PASSCODE = ")[^"]*(";)'
    html_content, count = re.subn(passcode_pattern, rf'\g<1>{passcode}\g<2>', html_content)
    if count > 0:
        print(f"   🔒 index.html 내부 패스코드를 [{passcode}](으)로 업데이트 완료!")
    else:
        print("   ⚠️ index.html 내부에서 CORRECT_PASSCODE 정의 마커를 찾지 못했습니다.")
        
    # 거대한 JSON 데이터 배열을 보기 좋게 직렬화 (들여쓰기 4칸 적용)
    json_data_str = json.dumps(records, ensure_ascii=False, indent=4)
    
    # index.html 내의 MOCK_DATA 변수 시작점과 돔 바인딩 시작점 검색
    start_marker = "const MOCK_DATA = ["
    end_marker = "        // DOM 요소들 바인딩"
    
    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        raise ValueError("❌ index.html 내부에서 데이터 교체 지점 마커(MOCK_DATA/DOM 바인딩)를 찾지 못했습니다.")
        
    # 교체용 데이터 블록 생성
    new_data_block = f"const MOCK_DATA = {json_data_str};\n\n"
    
    # 덮어쓰기 조립
    updated_html = html_content[:start_idx] + new_data_block + html_content[end_idx:]
    
    # 🚨 추가 패치: Papa.parse 수신 데이터 매핑 패치 🚨
    old_parse_target = "allData = results.data;"
    new_parse_block = """allData = results.data.map(item => {
                            return {
                                "시도": (item["지역(도/시)"] || item["시도"] || "").trim(),
                                "구군": (item["지역(시/군/구)"] || item["구군"] || "").trim(),
                                "서비스명": (item["서비스명"] || "").trim(),
                                "소관기관명": (item["소관기관명"] || "").trim(),
                                "서비스분야": (item["서비스분야"] || "").trim(),
                                "지원구분": (item["지원구분"] || "").trim(),
                                "신청기한": (item["신청기한"] || "").trim(),
                                "지원내용": (item["지원내용"] || "").trim(),
                                "지원대상": (item["지원대상"] || "").trim(),
                                "신청방법": (item["신청방법"] || "").trim(),
                                "정보수정일": (item["정보수정일"] || "").trim()
                            };
                        }).filter(item => item["서비스명"]);"""
                        
    if old_parse_target in updated_html:
        print("   ⚡ Papa.parse 데이터 매핑 패치 적용 중...")
        updated_html = updated_html.replace(old_parse_target, new_parse_block)
    
    with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_html)
        
    print(f"✨ {HTML_FILE_PATH} 파일 내에 1만 건 데이터 주입 및 매핑 패치 완료! (용량: {os.path.getsize(HTML_FILE_PATH)} Bytes)")

if __name__ == "__main__":
    try:
        data = download_and_parse_sheet()
        inject_data_to_html(data)
        print("\n==================================================")
        print("🏆🏆🏆 [데이터 내장 이식 성공] 구글 시트 내용이 홈페이지에 오프라인 탑재되었습니다!")
        print("==================================================")
    except Exception as e:
        print(f"🚨 [에러] 데이터 인젝터 구동 실패: {e}")
        sys.exit(1)
