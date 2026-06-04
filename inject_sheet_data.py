# -*- coding: utf-8 -*-
"""
🚀 안토부장 구글 시트 1만 건 데이터 내장 자동화 인젝터 (inject_sheet_data.py)
- 구글 스프레드시트의 원본 CSV 데이터를 직접 긁어와서 파싱
- 정제한 데이터를 index.html의 로컬 데이터베이스 영역에 완전 주입
- 오프라인 환경에서도 CORS 차단 없이 1초 만에 로딩 완료
- [v3] 4열 멀티체크박스 필터 자동 패치 & 패스코드 세션 만료 자동화 적용
"""

import os
import sys
import csv
import json
import re
import urllib.request

# UTF-8 출력 설정
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

CSV_EXPORT_URL = 'https://docs.google.com/spreadsheets/d/1uW5z-CAxD7vGQ5X8e3de6CdgTDBfKPGtXJlm9ENCMWw/export?format=csv'
HTML_FILE_PATH = 'index.html'

def clean_support_type(raw_val):
    if not raw_val:
        return "기타"
    raw_val = raw_val.strip()
    if any(k in raw_val for k in ["융자", "보증", "보험", "대출", "금융"]):
        return "대출/보증/금융"
    elif any(k in raw_val for k in ["현금", "지원금", "수당", "장학금", "감면"]):
        return "보조금/현금지원"
    elif any(k in raw_val for k in ["이용권", "현물", "바우처", "시설이용"]):
        return "바우처/현물지원"
    elif any(k in raw_val for k in ["교육", "기술지원", "상담", "법률", "컨설팅", "멘토링"]):
        return "교육/컨설팅/기술지원"
    elif any(k in raw_val for k in ["의료", "돌봄", "일자리", "복지", "서비스"]):
        return "의료/돌봄/복지서비스"
    return "기타"

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
        lines = content.splitlines()
        reader = csv.DictReader(lines)
        rows = list(reader)
        
        print(f"   📋 CSV 레코드 개수: {len(rows)}")
        
        required_headers = [
            "시도", "구군", "서비스명", "소관기관명", "서비스분야", 
            "지원구분", "신청기한", "지원내용", "지원대상", "신청방법", "정보수정일"
        ]
        
        # 1. 시도 명칭 표준화 헬퍼 함수
        def get_norm_sido(raw_sido):
            if not raw_sido:
                return "전국"
            raw_sido = raw_sido.strip()
            SIDO_NATIONAL = {"-", "", "전국", "중앙/공공", "중앙/전국", "중앙", "공공", "전체"}
            if raw_sido in SIDO_NATIONAL or raw_sido.startswith("중앙"):
                return "전국"
            
            sido_mapping = {
                "서울특별시": "서울", "서울시": "서울",
                "부산광역시": "부산", "부산시": "부산",
                "대구광역시": "대구", "대구시": "대구",
                "인천광역시": "인천", "인천시": "인천",
                "광주광역시": "광주", "광주시": "광주",
                "대전광역시": "대전", "대전시": "대전",
                "울산광역시": "울산", "울산시": "울산",
                "세종특별자치시": "세종", "세종시": "세종",
                "경기도": "경기",
                "강원특별자치도": "강원", "강원도": "강원",
                "충청북도": "충북",
                "충청남도": "충남",
                "전라북도": "전북", "전북특별자치도": "전북",
                "전라남도": "전남",
                "경상북도": "경북",
                "경상남도": "경남",
                "제주특별자치도": "제주", "제주시": "제주", "제주도": "제주"
            }
            return sido_mapping.get(raw_sido, raw_sido)

        # 2. 동적 구군 표준명칭 매핑 테이블 빌드
        gugun_map = {}  # key: (norm_sido, short_gugun), value: standard_gugun
        for row in rows:
            raw_sido = row.get("지역(도/시)", row.get("시도", ""))
            norm_sido = get_norm_sido(raw_sido)
            
            raw_gugun = row.get("지역(시/군/구)", row.get("구군", ""))
            if raw_gugun:
                raw_gugun = raw_gugun.strip()
                GUGUN_ALL = {"-", "", "−", "–", "전체", "전지역", "해당없음", "없음"}
                if raw_gugun not in GUGUN_ALL:
                    # 끝자리가 시/군/구 로 끝나는 표준값 탐색
                    if len(raw_gugun) >= 2 and (raw_gugun.endswith("시") or raw_gugun.endswith("군") or raw_gugun.endswith("구")):
                        short_gugun = raw_gugun[:-1]
                        gugun_map[(norm_sido, short_gugun)] = raw_gugun

        # 하드코딩 교정 룰 (테이블 누락 대비 방어 코드)
        hard_rules = {
            "군포": "군포시", "상주": "상주시", "여주": "여주시", "양평": "양평군",
            "강릉": "강릉시", "강진": "강진군", "거제": "거제시", "경산": "경산시",
            "경주": "경주시", "공주": "공주시", "광명": "광명시", "광산": "광산구",
            "구미": "구미시", "군산": "군산시", "김포": "김포시", "김해": "김해시",
            "목포": "목포시", "문경": "문경시", "보령": "보령시", "부천": "부천시",
            "사천": "사천시", "서산": "서산시", "성남": "성남시", "속초": "속초시",
            "수원": "수원시", "순천": "순천시", "시흥": "시흥시", "아산": "아산시",
            "안동": "안동시", "안산": "안산시", "안양": "안양시", "양산": "양산시",
            "양주": "양주시", "여수": "여수시", "영주": "영주시", "영천": "영천시",
            "용인": "용인시", "원주": "원주시", "의성": "의성군", "전주": "전주시",
            "제주": "제주시", "진주": "진주시", "창원": "창원시", "천안": "천안시",
            "청주": "청주시", "춘천": "춘천시", "충주": "충주시", "태백": "태백시",
            "통영": "통영시", "파주": "파주시", "평택": "평택시", "포천": "포천시",
            "포항": "포항시", "하남": "하남시", "화성": "화성시"
        }

        # 3. 레코드 파싱 및 정제 루프
        parsed_records = []
        for row in rows:
            record = {}
            for h in required_headers:
                val = ""
                if h == "시도":
                    raw_sido = row.get("지역(도/시)", row.get("시도", ""))
                    val = get_norm_sido(raw_sido)
                    record[h] = val
                    continue
                elif h == "구군":
                    raw_gugun = row.get("지역(시/군/구)", row.get("구군", ""))
                    val = raw_gugun.strip() if raw_gugun else ""
                    GUGUN_ALL = {"-", "", "−", "–", "전체", "전지역", "해당없음", "없음"}
                    if val in GUGUN_ALL:
                        val = "전지역"
                    else:
                        # 끝자리가 시/군/구로 끝나지 않는 비표준 명칭 정제
                        if len(val) >= 2 and not (val.endswith("시") or val.endswith("군") or val.endswith("구")):
                            sido_val = record.get("시도", "전국")
                            # 1) 동적 매핑 딕셔너리 조회
                            if (sido_val, val) in gugun_map:
                                val = gugun_map[(sido_val, val)]
                            # 2) 방어 룰 조회
                            elif val in hard_rules:
                                val = hard_rules[val]
                        
                        # 최종 추가 방어 예외 (예: 시도와 결합하지 않은 단순 하드코딩 매칭)
                        if val in hard_rules:
                            val = hard_rules[val]
                            
                    record[h] = val
                    continue
                else:
                    val = row.get(h, "")
                
                if h == "지원구분":
                    val = clean_support_type(val)
                    
                record[h] = val.strip() if val else ""
            
            if record["서비스명"]:
                parsed_records.append(record)
                
        print(f"   📊 파싱 성공: 총 {len(parsed_records)}건의 지원금 혜택 레코드 추출 완료!")
        return parsed_records
        
    except Exception as e:
        print(f"🚨 구글 시트 데이터 다운로드/파싱 실패: {e}")
        raise e

def patch_js_filter_code(html_content):
    if "container-sido" in html_content and "containerSido" in html_content:
        print("   ℹ️  이미 다중 선택 필터 및 JS 로직 패치가 완료되어 있습니다. 패치를 건너뜁니다.")
        return html_content
    print("   🔧 HTML 및 JS 필터 영역 패치 시작...")

    # ===== CSS 레이아웃 및 커스텀 멀티셀렉트 스타일 주입 =====
    old_css_grid = """        .filter-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }"""
        
    new_css_grid = """        .filter-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        
        /* 커스텀 멀티 셀렉트 드롭다운 스타일 */
        .custom-select-container {
            position: relative;
            width: 100%;
            font-family: var(--font-stack);
        }
        .custom-select-trigger {
            width: 100%;
            padding: 12px 16px;
            font-size: 15px;
            font-weight: 500;
            color: var(--ink-black);
            background-color: #fafdff;
            border: 1px solid var(--hairline);
            border-radius: 12px;
            text-align: left;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
        }
        .custom-select-trigger:after {
            content: '';
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid var(--ink-muted-48);
            margin-left: 10px;
            transition: transform 0.2s ease;
        }
        .custom-select-container.open .custom-select-trigger {
            border-color: var(--primary-blue);
        }
        .custom-select-container.open .custom-select-trigger:after {
            transform: rotate(180deg);
        }
        .custom-select-options {
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background-color: #ffffff;
            border: 1px solid var(--hairline);
            border-radius: 12px;
            margin-top: 6px;
            max-height: 250px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            padding: 8px;
        }
        .custom-select-container.open .custom-select-options {
            display: block;
        }
        .custom-select-option {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.15s ease;
            font-size: 14px;
            user-select: none;
            color: var(--ink-black);
        }
        .custom-select-option:hover {
            background-color: var(--canvas-parchment);
        }
        .custom-select-option input[type="checkbox"] {
            margin-right: 10px;
            width: 16px;
            height: 16px;
            cursor: pointer;
            accent-color: var(--primary-blue);
        }"""
        
    if old_css_grid in html_content:
        html_content = html_content.replace(old_css_grid, new_css_grid)
        print("   ✅ CSS 필터 그리드를 4열로 개편하고 멀티셀렉트 스타일 주입 완료!")

    # ===== HTML 필터 영역 멀티체크박스로 변경 =====
    old_html_block = """                    <!-- 시도 선택 -->
                    <div class="filter-item">
                        <label class="filter-label" for="select-sido">1단계: 시도 선택</label>
                        <select id="select-sido" class="form-select">
                            <option value="">전체 (전국)</option>
                        </select>
                    </div>
                    <!-- 구군 선택 -->
                    <div class="filter-item">
                        <label class="filter-label" for="select-gugun">2단계: 시군구 선택</label>
                        <select id="select-gugun" class="form-select" disabled>
                            <option value="">시도를 먼저 선택해 주세요</option>
                        </select>
                    </div>
                    <!-- 지원 형태 -->
                    <div class="filter-item">
                        <label class="filter-label" for="select-type">지원 형태</label>
                        <select id="select-type" class="form-select">
                            <option value="">전체 지원형태</option>
                        </select>
                    </div>"""

    new_html_block = """                    <!-- 시도 선택 -->
                    <div class="filter-item">
                        <label class="filter-label">1단계: 시도 선택 (중복 가능)</label>
                        <div class="custom-select-container" id="container-sido">
                            <button type="button" class="custom-select-trigger">전체 (시도)</button>
                            <div class="custom-select-options" id="options-sido"></div>
                        </div>
                    </div>
                    <!-- 구군 선택 -->
                    <div class="filter-item">
                        <label class="filter-label">2단계: 구/군 선택 (중복 가능)</label>
                        <div class="custom-select-container" id="container-gugun">
                            <button type="button" class="custom-select-trigger" id="trigger-gugun" disabled>시도를 먼저 선택하세요</button>
                            <div class="custom-select-options" id="options-gugun"></div>
                        </div>
                    </div>
                    <!-- 서비스 분야 -->
                    <div class="filter-item">
                        <label class="filter-label">서비스 분야 (중복 가능)</label>
                        <div class="custom-select-container" id="container-sector">
                            <button type="button" class="custom-select-trigger">전체 서비스분야</button>
                            <div class="custom-select-options" id="options-sector"></div>
                        </div>
                    </div>
                    <!-- 지원 형태 -->
                    <div class="filter-item">
                        <label class="filter-label">지원 형태 (중복 가능)</label>
                        <div class="custom-select-container" id="container-type">
                            <button type="button" class="custom-select-trigger">전체 지원형태</button>
                            <div class="custom-select-options" id="options-type"></div>
                        </div>
                    </div>"""

    if old_html_block in html_content:
        html_content = html_content.replace(old_html_block, new_html_block)
        print("   ✅ HTML 필터 영역에 서비스분야 및 멀티셀렉트 레이아웃 탑재 완료!")
    else:
        grid_start_idx = html_content.find('<div class="filter-grid">')
        if grid_start_idx >= 0:
            grid_end_idx = html_content.find('</div>', html_content.find('<!-- 텍스트 검색 -->', grid_start_idx))
            if grid_end_idx >= 0:
                grid_end_real = html_content.rfind('</div>', grid_start_idx, html_content.find('<!-- 텍스트 검색 -->'))
                if grid_end_real >= 0:
                    html_content = html_content[:grid_start_idx + len('<div class="filter-grid">')] + "\n" + new_html_block + "\n" + html_content[grid_end_real:]
                    print("   ✅ HTML 필터 영역을 그리드 마커 방식으로 안전 치환 완료!")

    # ===== JS DOM 바인딩 및 커스텀 드롭다운 로직 주입 =====
    old_dom_binding = """        // DOM 요소들 바인딩
        const statusBadge = document.getElementById('connection-status');
        const selectSido = document.getElementById('select-sido');
        const selectGugun = document.getElementById('select-gugun');
        const selectType = document.getElementById('select-type');
        const searchInput = document.getElementById('search-input');
        const btnReset = document.getElementById('btn-reset');
        const cardsContainer = document.getElementById('cards-container');
        const totalCountSpan = document.getElementById('total-count');
        const currentCountSpan = document.getElementById('current-count');
        const loaderArea = document.getElementById('loader-area');
        const btnLoadMore = document.getElementById('btn-load-more');"""

    new_dom_binding = """        // DOM 요소들 바인딩
        const statusBadge = document.getElementById('connection-status');
        const containerSido = document.getElementById('container-sido');
        const containerGugun = document.getElementById('container-gugun');
        const containerSector = document.getElementById('container-sector');
        const containerType = document.getElementById('container-type');
        const searchInput = document.getElementById('search-input');
        const btnReset = document.getElementById('btn-reset');
        const cardsContainer = document.getElementById('cards-container');
        const totalCountSpan = document.getElementById('total-count');
        const currentCountSpan = document.getElementById('current-count');
        const btnLoadMore = document.getElementById('btn-load-more');
        const loaderArea = document.getElementById('loader-area');

        // 커스텀 드롭다운 열기/닫기 토글
        document.addEventListener('click', function(e) {
            const trigger = e.target.closest('.custom-select-trigger');
            if (trigger) {
                e.stopPropagation();
                const container = trigger.parentElement;
                
                // 구군의 경우 disabled 면 작동 금지
                if (container.id === 'container-gugun' && trigger.hasAttribute('disabled')) {
                    return;
                }

                // 다른 열려있는 드롭다운 모두 닫기
                document.querySelectorAll('.custom-select-container').forEach(c => {
                    if (c !== container) c.classList.remove('open');
                });
                
                container.classList.toggle('open');
            } else {
                // 외부 클릭 시 모든 드롭다운 닫기
                document.querySelectorAll('.custom-select-container').forEach(c => {
                    c.classList.remove('open');
                });
            }
        });

        // 드롭다운 옵션 내부 클릭 시 닫히지 않도록 이벤트 전파 차단
        document.addEventListener('click', function(e) {
            if (e.target.closest('.custom-select-options')) {
                e.stopPropagation();
            }
        });

        // 선택된 값들을 수집하는 헬퍼 함수
        function getSelectedValues(containerId) {
            const container = document.getElementById(containerId);
            if (!container) return [];
            const checkedBoxes = container.querySelectorAll('.custom-select-options input[type="checkbox"]:checked');
            return Array.from(checkedBoxes).map(cb => cb.value);
        }

        // 선택 완료 후 트리거 텍스트를 업데이트하는 함수
        function updateTriggerText(containerId, defaultText) {
            const container = document.getElementById(containerId);
            if (!container) return;
            const trigger = container.querySelector('.custom-select-trigger');
            const selected = getSelectedValues(containerId);
            
            if (selected.length === 0) {
                trigger.textContent = defaultText;
            } else if (selected.length === 1) {
                trigger.textContent = selected[0];
            } else {
                trigger.textContent = `${selected[0]} 외 ${selected.length - 1}건`;
            }
        }"""

    if old_dom_binding in html_content:
        html_content = html_content.replace(old_dom_binding, new_dom_binding)
        print("   ✅ JS DOM 바인딩 및 커스텀 드롭다운 공통로직 업데이트 완료!")
    else:
        dom_start = html_content.find("        // DOM 요소들 바인딩")
        if dom_start >= 0:
            dom_end = html_content.find("btn-load-more');", dom_start)
            if dom_end >= 0:
                html_content = html_content[:dom_start] + new_dom_binding + html_content[dom_end + len("btn-load-more');"):]
                print("   ✅ JS DOM 바인딩을 강제 마커 슬라이싱 방식으로 리뉴얼 완료!")

    # ===== JS addEventListener 이벤트 핸들러 제거 =====
    old_listeners = """            selectSido.addEventListener('change', handleSidoChange);
            selectGugun.addEventListener('change', applyFilters);
            selectType.addEventListener('change', applyFilters);"""

    if old_listeners in html_content:
        html_content = html_content.replace(old_listeners, "")
        print("   ✅ JS addEventListener 단일 드롭다운용 삭제 완료!")

    # ===== JS 데이터 매핑 커스텀화 =====
    old_parse_target = "allData = results.data;"
    new_parse_block = """allData = results.data.map(item => {
                            const rawSido = (item["지역(도/시)"] || item["시도"] || "").trim();
                            const SIDO_NATIONAL = new Set(["-", "", "전국", "중앙/공공", "중앙/전국", "중앙", "공공", "전체"]);
                            const normSido = (SIDO_NATIONAL.has(rawSido) || rawSido.startsWith("중앙")) ? "전국" : rawSido;
                            
                            const rawGugun = (item["지역(시/군/구)"] || item["구군"] || "").trim();
                            const GUGUN_ALL = new Set(["-", "", "−", "–", "전체", "전지역", "해당없음", "없음"]);
                            const normGugun = GUGUN_ALL.has(rawGugun) ? "전지역" : rawGugun;
                            
                            const rawType = (item["지원구분"] || "").trim();
                            let normType = "기타";
                            if (rawType) {
                                if (rawType.includes("융자") || rawType.includes("보증") || rawType.includes("보험") || rawType.includes("대출") || rawType.includes("금융")) {
                                    normType = "대출/보증/금융";
                                } else if (rawType.includes("현금") || rawType.includes("지원금") || rawType.includes("수당") || rawType.includes("장학금") || rawType.includes("감면")) {
                                    normType = "보조금/현금지원";
                                } else if (rawType.includes("이용권") || rawType.includes("현물") || rawType.includes("바우처") || rawType.includes("시설이용")) {
                                    normType = "바우처/현물지원";
                                } else if (rawType.includes("교육") || rawType.includes("기술지원") || rawType.includes("상담") || rawType.includes("법률") || rawType.includes("컨설팅") || rawType.includes("멘토링")) {
                                    normType = "교육/컨설팅/기술지원";
                                } else if (rawType.includes("의료") || rawType.includes("돌봄") || rawType.includes("일자리") || rawType.includes("복지") || rawType.includes("서비스")) {
                                    normType = "의료/돌봄/복지서비스";
                                }
                            }
                            
                            return {
                                "시도": normSido,
                                "구군": normGugun,
                                "서비스명": (item["서비스명"] || "").trim(),
                                "소관기관명": (item["소관기관명"] || "").trim(),
                                "서비스분야": (item["서비스분야"] || "").trim(),
                                "지원구분": normType,
                                "신청기한": (item["신청기한"] || "").trim(),
                                "지원내용": (item["지원내용"] || "").trim(),
                                "지원대상": (item["지원대상"] || "").trim(),
                                "신청방법": (item["신청방법"] || "").trim(),
                                "정보수정일": (item["정보수정일"] || "").trim()
                            };
                        }).filter(item => item["서비스명"]);"""
                        
    if old_parse_target in html_content:
        html_content = html_content.replace(old_parse_target, new_parse_block)
        print("   ⚡ Papa.parse 데이터 정제 맵 이식 완료!")

    # ===== JS 필터 관련 주요 함수들(applyFilters, initFilters, handleSidoChange, resetFilters) 재설계 =====
    new_apply_filters = """function applyFilters() {
            const selectedSidos = getSelectedValues('container-sido');
            const selectedGuguns = getSelectedValues('container-gugun');
            const selectedSectors = getSelectedValues('container-sector');
            const selectedTypes = getSelectedValues('container-type');
            const searchQuery = searchInput.value.trim().toLowerCase();

            filteredData = allData.filter(item => {
                if (selectedSidos.length > 0 && !selectedSidos.includes(item['시도'])) return false;
                if (selectedGuguns.length > 0 && !selectedGuguns.includes(item['구군'])) return false;
                if (selectedSectors.length > 0 && !selectedSectors.includes(item['서비스분야'])) return false;
                if (selectedTypes.length > 0 && !selectedTypes.includes(item['지원구분'])) return false;
                
                if (searchQuery) {
                    const sName = (item['서비스명'] || '').toLowerCase();
                    const sAgency = (item['소관기관명'] || '').toLowerCase();
                    const sContent = (item['지원내용'] || '').toLowerCase();
                    const sTarget = (item['지원대상'] || '').toLowerCase();
                    if (!sName.includes(searchQuery) && 
                        !sAgency.includes(searchQuery) && 
                        !sContent.includes(searchQuery) && 
                        !sTarget.includes(searchQuery)) {
                        return false;
                    }
                }
                return true;
            });

            currentLimit = CHUNK_SIZE;
            renderCards();
        }"""

    new_init_filters = """function initFilters() {
            // 1. 시도 목록 수집 및 렌더링
            let sidos = [...new Set(allData.map(item => item['시도']))].filter(Boolean).sort();
            const hasNational = sidos.includes('전국');
            if (hasNational) {
                sidos = sidos.filter(s => s !== '전국');
            }
            
            const optionsSido = document.getElementById('options-sido');
            optionsSido.innerHTML = '';
            
            if (hasNational) {
                createCheckboxOption(optionsSido, '전국', '전국 (중앙/전국 단위 지원)', 'container-sido', '전체 (시도)', handleSidoChange);
            }
            sidos.forEach(sido => {
                createCheckboxOption(optionsSido, sido, sido, 'container-sido', '전체 (시도)', handleSidoChange);
            });

            // 2. 서비스분야 목록 수집 및 렌더링
            const sectors = [...new Set(allData.map(item => item['서비스분야']))].filter(Boolean).sort();
            const optionsSector = document.getElementById('options-sector');
            optionsSector.innerHTML = '';
            sectors.forEach(sector => {
                createCheckboxOption(optionsSector, sector, sector, 'container-sector', '전체 서비스분야', applyFilters);
            });

            // 3. 지원구분 목록 수집 및 렌더링
            const types = [...new Set(allData.map(item => item['지원구분']))].filter(Boolean).sort();
            const optionsType = document.getElementById('options-type');
            optionsType.innerHTML = '';
            types.forEach(type => {
                createCheckboxOption(optionsType, type, type, 'container-type', '전체 지원형태', applyFilters);
            });

            // 구군 비활성화 초기화
            const triggerGugun = document.getElementById('trigger-gugun');
            triggerGugun.textContent = '시도를 먼저 선택하세요';
            triggerGugun.disabled = true;
            document.getElementById('options-gugun').innerHTML = '';
        }

        // 체크박스 옵션을 생성하는 도우미 함수
        function createCheckboxOption(parentEl, value, labelText, containerId, defaultText, changeCallback) {
            const label = document.createElement('label');
            label.className = 'custom-select-option';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = value;
            
            checkbox.addEventListener('change', () => {
                updateTriggerText(containerId, defaultText);
                if (changeCallback) changeCallback();
            });
            
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(labelText));
            parentEl.appendChild(label);
        }"""

    new_handle_sido = """function handleSidoChange() {
            const selectedSidos = getSelectedValues('container-sido');
            const triggerGugun = document.getElementById('trigger-gugun');
            const optionsGugun = document.getElementById('options-gugun');
            
            if (selectedSidos.length === 0) {
                triggerGugun.textContent = '시도를 먼저 선택하세요';
                triggerGugun.disabled = true;
                optionsGugun.innerHTML = '';
                applyFilters();
                return;
            }

            // 선택된 모든 시도에 소속된 구군 목록 추출
            const filteredGuguns = allData
                .filter(item => selectedSidos.includes(item['시도']))
                .map(item => item['구군'])
                .filter(Boolean);
                
            const uniqueGuguns = [...new Set(filteredGuguns)].sort();
            const gugunList = uniqueGuguns.filter(g => g !== '전지역');
            const hasAllRegion = uniqueGuguns.includes('전지역');

            optionsGugun.innerHTML = '';
            
            if (hasAllRegion) {
                createCheckboxOption(optionsGugun, '전지역', '전지역 (전 지역 해당 혜택)', 'container-gugun', '전체 구/군', applyFilters);
            }
            gugunList.forEach(gugun => {
                createCheckboxOption(optionsGugun, gugun, gugun, 'container-gugun', '전체 구/군', applyFilters);
            });
            
            triggerGugun.disabled = false;
            updateTriggerText('container-gugun', '전체 구/군');
            
            applyFilters();
        }"""

    new_reset_filters = """function resetFilters() {
            // 모든 체크박스 해제
            document.querySelectorAll('.custom-select-options input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });
            
            // 모든 트리거 텍스트 초기화
            updateTriggerText('container-sido', '전체 (시도)');
            updateTriggerText('container-sector', '전체 서비스분야');
            updateTriggerText('container-type', '전체 지원형태');
            
            // 구군 초기화
            const triggerGugun = document.getElementById('trigger-gugun');
            triggerGugun.textContent = '시도를 먼저 선택하세요';
            triggerGugun.disabled = true;
            document.getElementById('options-gugun').innerHTML = '';
            
            searchInput.value = "";
            applyFilters();
        }"""

    def safe_replace_func(old_name, new_code, end_marker_list):
        nonlocal html_content
        start_idx = html_content.find(f"function {old_name}()")
        if start_idx >= 0:
            end_idx = -1
            for em in end_marker_list:
                end_idx = html_content.find(em, start_idx)
                if end_idx >= 0:
                    end_idx += len(em)
                    break
            if end_idx >= 0:
                html_content = html_content[:start_idx] + new_code + html_content[end_idx:]
                print(f"   ✅ {old_name}() 함수 패치 성공!")
                return True
        print(f"   ⚠️ {old_name}() 마커를 찾지 못했습니다.")
        return False

    safe_replace_func("applyFilters", new_apply_filters, ["renderCards();\n        }", "renderCards();\r\n        }"])
    safe_replace_func("initFilters", new_init_filters, ["selectGugun.disabled = true;\n        }", "selectGugun.disabled = true;\r\n        }"])
    safe_replace_func("handleSidoChange", new_handle_sido, ["applyFilters();\n        }", "applyFilters();\r\n        }"])
    safe_replace_func("resetFilters", new_reset_filters, ["applyFilters();\n        }", "applyFilters();\r\n        }"])

    return html_content

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

    # HTML 헤더 보안 게이트 교체 (인증 저장소를 salim_passcode 로 전환)
    old_gate = "try{if(localStorage.getItem('salim_auth')!=='true'){location.replace('./lock.html');}}catch(e){}"
    new_gate = f'const CORRECT_PASSCODE = "{passcode}"; try{{if(localStorage.getItem("salim_passcode")!==CORRECT_PASSCODE){{location.replace("./lock.html");}}}}catch(e){{}}'
    
    if old_gate in html_content:
        html_content = html_content.replace(old_gate, new_gate)
        print("   🔒 index.html 헤더 보안 게이트를 패스코드 실시간 매칭방식으로 업그레이드 완료!")
    else:
        html_content, count = re.subn(r'const CORRECT_PASSCODE = "[^"]*";', f'const CORRECT_PASSCODE = "{passcode}";', html_content)
        if count > 0:
            print(f"   🔒 index.html 내부 패스코드를 [{passcode}](으)로 업데이트 완료!")
        else:
            head_tag = "<head>"
            head_idx = html_content.find(head_tag)
            if head_idx >= 0:
                script_block = f'\n    <script>{new_gate}</script>'
                html_content = html_content[:head_idx + len(head_tag)] + script_block + html_content[head_idx + len(head_tag):]
                print("   🔒 index.html 상단에 보안 게이트 스크립트 신규 이식 완료!")

    # lock.html 내부의 비밀번호도 함께 주입 패치
    LOCK_FILE_PATH = 'lock.html'
    if os.path.exists(LOCK_FILE_PATH):
        try:
            with open(LOCK_FILE_PATH, 'r', encoding='utf-8') as lf:
                lock_content = lf.read()
            
            lock_pw_pattern = r'(const CORRECT_PW = ")[^"]*(";\s*)'
            lock_content, count = re.subn(lock_pw_pattern, rf'\g<1>{passcode}\g<2>', lock_content)
            if count > 0:
                with open(LOCK_FILE_PATH, 'w', encoding='utf-8') as lf:
                    lf.write(lock_content)
                print(f"   🔒 lock.html 내부 비밀번호를 [{passcode}](으)로 업데이트 완료!")
            else:
                print("   ⚠️ lock.html 내부에서 CORRECT_PW 정의 마커를 찾지 못했습니다.")
        except Exception as le:
            print(f"   ⚠️ lock.html 패치 중 오류 발생: {le}")
        
    json_data_str = json.dumps(records, ensure_ascii=False, indent=4)
    
    start_marker = "const MOCK_DATA = ["
    end_markers = [
        "        // DOM 요소들 바인딩",
        "// DOM 요소들 바인딩",
        "        // DOM",
        "const selectSido",
    ]
    
    start_idx = html_content.find(start_marker)
    end_idx = -1
    for em in end_markers:
        end_idx = html_content.find(em, start_idx if start_idx >= 0 else 0)
        if end_idx >= 0:
            print(f"   📌 DOM 바인딩 마커 발견: '{em}'")
            break
    
    if start_idx == -1:
        raise ValueError("❌ index.html 내부에서 MOCK_DATA 시작 마커를 찾지 못했습니다.")
    if end_idx == -1:
        raise ValueError("❌ index.html 내부에서 DOM 바인딩 마커를 찾지 못했습니다.")
        
    new_data_block = f"const MOCK_DATA = {json_data_str};\n\n"
    updated_html = html_content[:start_idx] + new_data_block + html_content[end_idx:]
    print(f"   📊 MOCK_DATA 주입 완료: {len(records)}건")
    
    # ===== HTML 및 JS 필터 패치 =====
    updated_html = patch_js_filter_code(updated_html)
    
    with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_html)
        
    print(f"✨ {HTML_FILE_PATH} 파일 내에 데이터 주입 및 JS 필터 패치 완료! (용량: {os.path.getsize(HTML_FILE_PATH):,} Bytes)")

def auto_deploy():
    import subprocess
    from datetime import datetime

    print("\n🚀 Git 자동 배포 시작...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    cmds = [
        (["git", "add", "index.html", "lock.html"], "HTML 파일들 스테이징"),
        (["git", "commit", "-m", f"auto: 구글시트 최신 데이터 + 보안로그인 무효화 패치 ({now})"], "커밋"),
        (["git", "push", "origin", "main"], "GitHub Pages 배포"),
    ]

    for cmd, desc in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            print(f"   ✅ {desc} 완료")
        else:
            if "nothing to commit" in result.stdout + result.stderr:
                print(f"   ℹ️  {desc}: 변경사항 없음 (이미 최신)")
            else:
                print(f"   ⚠️  {desc} 출력: {result.stderr.strip()[:200]}")

    print("🌐 약 30초 후 살림 Botaem 사이트에 자동 반영됩니다!")

if __name__ == "__main__":
    try:
        data = download_and_parse_sheet()
        inject_data_to_html(data)
        print("\n==================================================")
        print("🏆🏆🏆 [데이터 내장 이식 성공] 구글 시트 내용이 홈페이지에 탑재되었습니다!")
        print("==================================================")
        auto_deploy()
    except Exception as e:
        print(f"🚨 [E러] 데이터 인젝터 구동 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
