import os

html_path = r"c:\Users\bwj10\OneDrive\바탕 화면\AI_Agents\다니 디자인 에이전트\살림 Botaem 홈페이지 프로젝트\index.html"

if os.path.exists(html_path):
    print("Reading HTML...")
    # UTF-8로 읽기 시도
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(html_path, "r", encoding="cp949") as f:
            content = f.read()
            
    print("Modifying content...")
    # 캐시 버스팅 및 한글 깨짐 수정
    # 1. hero_illustration.png -> hero_illustration.png?v=2
    # 2. 깨진 alt 텍스트 수정
    target_img_tag = 'src="hero_illustration.png"'
    replacement_img_tag = 'src="hero_illustration.png?v=2"'
    
    if target_img_tag in content:
        content = content.replace(target_img_tag, replacement_img_tag)
        print("Replaced image src successfully.")
    else:
        print("Image tag src not found, maybe already replaced?")

    # alt 속성이 깨진 부분을 좀 더 범용적으로 찾아서 변경
    # "hero_illustration.png" 근처의 alt 속성을 변경
    import re
    # <img src="hero_illustration.png(?:\\?v=\\d+)?" alt="[^"]*" class="hero-main-img"> 패턴 찾기
    pattern = r'(<img src="hero_illustration.png(?:\?v=\d+)?" alt=")[^"]*(" class="hero-main-img">)'
    content, count = re.subn(pattern, r'\g<1>살림 Botaem 이웃들\g<2>', content)
    print(f"Replaced {count} alt text occurrences.")

    # 저장하기
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("HTML patch saved in UTF-8 format.")
else:
    print("HTML file not found!")
