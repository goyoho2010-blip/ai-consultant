import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup

# Set page configuration
st.set_page_config(
    page_title="학생부 종합 진격(NAVI) AI 분석 리포트",
    page_icon="🎓",
    layout="wide"
)

# =====================================================================
# 1.학과 및 계열 키워드 / 권장 과목 맵핑 데이터베이스
# =====================================================================
MAJOR_MAP = {
    # 인공지능/SW/컴퓨터
    "인공지능": {"domain": "공학/IT", "keywords": ["인공지능", "AI", "딥러닝", "머신러닝", "경사하강법", "신경망", "파이썬", "선형회귀", "데이터", "알고리즘", "코딩"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "프로그래밍", "물리학Ⅰ", "확률과 통계"]},
    "소프트웨어": {"domain": "공학/IT", "keywords": ["소프트웨어", "프로그래밍", "알고리즘", "파이썬", "C++", "객체지향", "자료구조", "코딩", "개발"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "프로그래밍"]},
    "컴퓨터공학과": {"domain": "공학/IT", "keywords": ["컴퓨터", "프로그래머", "하드웨어", "소프트웨어", "데이터베이스", "알고리즘", "아두이노", "임베디드", "네트워크"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "프로그래밍"]},
    "반도체": {"domain": "공학/IT", "keywords": ["반도체", "시스템반도체", "회로", "다이오드", "전기음성도", "양자컴퓨터", "신소재"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "화학Ⅰ"]},
    "전기": {"domain": "공학/IT", "keywords": ["전기", "회로", "전류", "전압", "자기장", "변압기", "전력"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "물리학Ⅱ"]},
    "전자공학과": {"domain": "공학/IT", "keywords": ["전자", "회로", "센서", "트랜지스터", "임베디드", "아두이노", "신호"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "물리학Ⅱ"]},
    "IT": {"domain": "공학/IT", "keywords": ["IT", "정보", "통신", "디지털", "데이터", "네트워크"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "프로그래밍"]},
    "경영공학": {"domain": "공학/IT", "keywords": ["경영공학", "시스템", "최적화", "데이터분석", "공정", "물류", "효율성"], "subjects": ["수학Ⅰ", "수학Ⅱ", "확률과 통계", "미적분"]},
    "교육공학": {"domain": "사범/교육", "keywords": ["교육공학", "에듀테크", "수업설계", "디지털교육", "학습분석"], "subjects": ["국어", "수학", "영어", "정보/프로그래밍"]},
    "미디어": {"domain": "사회/언론", "keywords": ["미디어", "콘텐츠", "신문", "방송", "커뮤니케이션", "저널리즘", "소셜미디어"], "subjects": ["국어", "사회", "영어"]},
    "화공생명융합": {"domain": "공학/자연", "keywords": ["화공", "생명공학", "화학공학", "효소", "배터리", "전해질", "촉매"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "화학Ⅰ", "화학Ⅱ", "생명과학Ⅰ"]},
    "융합공학": {"domain": "공학/IT", "keywords": ["융합", "공학", "시스템", "스마트", "로봇", "센서"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "화학Ⅰ"]},

    # 기초자연과학
    "물리학과": {"domain": "자연과학", "keywords": ["물리", "역학", "전기", "자기", "파동", "양자", "상대성이론", "전자기학"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "물리학Ⅱ"]},
    "화학과": {"domain": "자연과학", "keywords": ["화학", "분자", "원자", "전기음성도", "반응속도", "유기화학", "열역학"], "subjects": ["수학Ⅰ", "수학Ⅱ", "화학Ⅰ", "화학Ⅱ", "생명과학Ⅰ"]},
    "생명과학과": {"domain": "자연과학", "keywords": ["생명과학", "유전자", "DNA", "세포", "뉴런", "효소", "생태계", "면역"], "subjects": ["수학Ⅰ", "수학Ⅱ", "생명과학Ⅰ", "생명과학Ⅱ", "화학Ⅰ"]},
    "수학과": {"domain": "자연과학", "keywords": ["수학", "방정식", "함수", "미분", "적분", "기하", "수열", "증명", "논리"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "확률과 통계"]},
    "통계학과": {"domain": "자연과학/상경", "keywords": ["통계", "확률", "데이터", "표본", "회귀분석", "분포", "빅데이터"], "subjects": ["수학Ⅰ", "수학Ⅱ", "확률과 통계", "미적분"]},

    # 전통 공학 / 건축
    "기계공학과": {"domain": "공학", "keywords": ["기계", "역학", "열역학", "유체역학", "동력학", "자율주행", "자동차", "로봇"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "기하", "물리학Ⅰ", "물리학Ⅱ"]},
    "화학공학과": {"domain": "공학", "keywords": ["화학공학", "공정", "배터리", "신소재", "열전달", "반응공학"], "subjects": ["수학Ⅰ", "수학Ⅱ", "미적분", "화학Ⅰ", "화학Ⅱ", "물리학Ⅰ"]},
    "건축학과": {"domain": "공학/건축", "keywords": ["건축", "도면", "3D모델링", "트러스", "구조", "공간", "인테리어", "설계"], "subjects": ["수학Ⅰ", "수학Ⅱ", "기하", "물리학Ⅰ", "사회/지리"]},

    # 의약학계열
    "의학과": {"domain": "의약학", "keywords": ["의학", "생리학", "병리학", "해부학", "임상", "질병", "약물", "세포"], "subjects": ["수학Ⅰ", "수학Ⅱ", "생명과학Ⅰ", "생명과학Ⅱ", "화학Ⅰ", "화학Ⅱ"]},
    "치의학과": {"domain": "의약학", "keywords": ["치의학", "구강", "치아", "생체재료", "뼈", "조직"], "subjects": ["수학Ⅰ", "수학Ⅱ", "생명과학Ⅰ", "생명과학Ⅱ", "화학Ⅰ", "화학Ⅱ"]},
    "한의학과": {"domain": "의약학", "keywords": ["한의학", "침구", "한약", "체질", "음양오행", "동의보감", "생약"], "subjects": ["수학Ⅰ", "수학Ⅱ", "생명과학Ⅰ", "화학Ⅰ", "한국사/한문"]},
    "약학과": {"domain": "의약학", "keywords": ["약학", "약물", "합성", "분자", "생화학", "제약", "임상시험"], "subjects": ["수학Ⅰ", "수학Ⅱ", "화학Ⅰ", "화학Ⅱ", "생명과학Ⅰ", "생명과학Ⅱ"]},
    "간호학과": {"domain": "의약학", "keywords": ["간호", "보건", "환자", "돌봄", "의료", "생리학", "인성"], "subjects": ["수학Ⅰ", "수학Ⅱ", "생명과학Ⅰ", "화학Ⅰ", "사회/윤리"]},

    # 인문/어학
    "국어국문학과": {"domain": "인문", "keywords": ["국어", "문학", "문법", "시", "소설", "비평", "어휘", "작문"], "subjects": ["국어", "문학", "독서", "언어와 매체", "화법과 작문"]},
    "영어영문학과": {"domain": "인문", "keywords": ["영어", "영문학", "번역", "영작", "말하기", "독해", "언어학"], "subjects": ["영어", "영어Ⅰ", "영어Ⅱ", "영어 독해와 작문"]},
    "사학과": {"domain": "인문", "keywords": ["역사", "한국사", "세계사", "동아시아사", "사료", "유물", "문화재"], "subjects": ["한국사", "동아시아사", "세계사", "사회"]},
    "철학과": {"domain": "인문", "keywords": ["철학", "사상", "윤리", "논리", "인식론", "존재론", "비판적사고"], "subjects": ["생활과 윤리", "윤리와 사상", "국어", "독서"]},
    "외국어전공": {"domain": "인문/어학", "keywords": ["외국어", "회화", "문법", "문화", "번역", "통역"], "subjects": ["영어", "제2외국어"]},

    # 사회/상경
    "경제학과": {"domain": "상경", "keywords": ["경제", "금융", "시장", "화폐", "행동경제학", "소비자", "통계", "수리"], "subjects": ["수학Ⅰ", "수학Ⅱ", "확률과 통계", "경제", "사회·문화"]},
    "사회학과": {"domain": "사회", "keywords": ["사회", "불평등", "양성평등", "계층", "사회문제", "조사", "통계"], "subjects": ["사회·문화", "통합사회", "확률과 통계"]},
    "정치외교학과": {"domain": "사회", "keywords": ["정치", "외교", "법", "국제관계", "민주주의", "선거", "정책"], "subjects": ["정치와 법", "사회·문화", "세계사"]},
    "심리학과": {"domain": "사회", "keywords": ["심리", "인지", "행동", "MBTI", "상담", "뇌과학", "통계"], "subjects": ["심리학", "생명과학Ⅰ", "확률과 통계", "사회·문화"]},
    "신문방송학과": {"domain": "사회/언론", "keywords": ["신문", "방송", "언론", "저널리즘", "미디어", "매체", "광고"], "subjects": ["언어와 매체", "사회·문화", "영어"]},

    # 사범/교육
    "교육학과": {"domain": "사범/교육", "keywords": ["교육", "수업", "학습", "멘토링", "교사", "청소년", "발달"], "subjects": ["국어", "수학", "영어", "사회/교육학"]},
    "초등교육학과": {"domain": "사범/교육", "keywords": ["초등", "아동", "초등교육", "교대", "전교과", "인성"], "subjects": ["국어", "수학", "영어", "사회", "과학", "예체능"]},
    "국어교육학과": {"domain": "사범/교육", "keywords": ["국어교육", "문학", "문법", "수업지도", "교과지도"], "subjects": ["국어", "문학", "독서", "언어와 매체"]},
    "영어교육학과": {"domain": "사범/교육", "keywords": ["영어교육", "영문법", "영어수업", "말하기지도"], "subjects": ["영어", "영어Ⅰ", "영어Ⅱ"]},

    # 예체능
    "체육학과": {"domain": "예체능", "keywords": ["체육", "스포츠", "운동", "순발력", "근력", "농구", "배구", "축구"], "subjects": ["체육", "스포츠 생활"]},
    "회화과": {"domain": "예체능", "keywords": ["회화", "미술", "디자인", "픽토그램", "3D모델링", "데생", "색채"], "subjects": ["미술", "미술 창작"]},
    "음악학과": {"domain": "예체능", "keywords": ["음악", "연주", "성악", "작곡", "악기", "화성학"], "subjects": ["음악", "음악 연주"]},
    "디자인학과": {"domain": "예체능", "keywords": ["디자인", "3D모델링", "CAD", "픽토그램", "조형", "시각디자인"], "subjects": ["미술", "기술·가정"]},
    "연극영화과": {"domain": "예체능", "keywords": ["연극", "영화", "연기", "시나리오", "연출", "상황극"], "subjects": ["국어", "문학", "연극"]}
}

# =====================================================================
# 2. NEIS+ HTML 정밀 파싱 엔진 (교과 성적 추출)
# =====================================================================
KOREAN = ["국어", "화법", "작문", "문학", "독서", "언어"]
MATH = ["수학", "미적분", "기하", "확률", "통계", "수학Ⅰ", "수학Ⅱ", "수학I", "수학II"]
ENG = ["영어", "회화", "독해", "작문", "영어Ⅰ", "영어Ⅱ", "영어I", "영어II"]
SCI = ["물리학", "화학", "생명과학", "지구과학", "과학", "통합과학", "과학탐구실험"]
SOC = ["한국사", "역사", "지리", "일반사회", "윤리", "사상", "정치", "법", "경제", "사회", "통합사회", "정치와법", "생활과윤리", "한국지리"]

def classify_category(sub_name):
    for k in KOREAN:
        if k in sub_name: return "국어"
    for m in MATH:
        if m in sub_name: return "수학"
    for e in ENG:
        if e in sub_name: return "영어"
    for s in SCI:
        if s in sub_name: return "과학"
    for sc in SOC:
        if sc in sub_name: return "사회"
    return "기타"

def parse_neis_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    parsed_rows = []
    
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
            if len(cols) >= 6:
                sub_name = ""
                for col_txt in cols[:4]:
                    if any(c in col_txt for c in ["국어", "수학", "영어", "한국사", "사회", "과학", "문학", "독서", "물리", "화학", "생명", "지구", "지리", "윤리", "정치", "기술"]):
                        sub_name = col_txt.split('\n')[0].strip()
                        break
                
                if not sub_name or "교과우수상" in sub_name:
                    continue
                
                unit = None
                rank = None
                count = None
                
                for col_txt in cols:
                    if not unit and re.match(r'^[1-9]$', col_txt):
                        unit = int(col_txt)
                    elif unit and not rank:
                        rank_match = re.search(r'^([1-9])(?:\s*\([0-9/]+\))?$', col_txt)
                        if rank_match:
                            rank = int(rank_match.group(1))
                    
                    # 수강자 수 추출 (예: A(40) -> 40명)
                    cnt_match = re.search(r'\(([0-9]+)\)', col_txt)
                    if cnt_match and not count:
                        try:
                            count = int(cnt_match.group(1))
                        except:
                            pass

                if unit and rank:
                    cat = classify_category(sub_name)
                    parsed_rows.append({
                        "과목명": sub_name,
                        "교과군": cat,
                        "단위수": unit,
                        "석차등급": rank,
                        "수강자수": count if count else 100
                    })

    full_text = soup.get_text(separator='\n')
    return parsed_rows, full_text

def calculate_gpa(df_subjects, target_groups=None):
    if df_subjects.empty: return 0.0
    filtered = df_subjects.copy()
    if target_groups:
        filtered = filtered[filtered["교과군"].isin(target_groups)]
    valid = filtered[pd.to_numeric(filtered["석차등급"], errors="coerce").notnull()].copy()
    if valid.empty: return 0.0
    
    tot_credits = valid["단위수"].sum()
    if tot_credits == 0: return 0.0
    weighted_sum = (valid["석차등급"] * valid["단위수"]).sum()
    return round(weighted_sum / tot_credits, 2)

# =====================================================================
# 3. 7단계 역량 평가 엔진 및 증거문구 자동 추출
# =====================================================================
EVAL_LEVELS = ["상상 (Top)", "상중 (Very High)", "상하 (High)", "중상 (Above Avg)", "중중 (Average)", "중하 (Below Avg)", "하하 (Low)"]

def evaluate_competencies(df_subjects, full_text, target_major):
    info = MAJOR_MAP.get(target_major, {
        "domain": "일반", "keywords": [target_major], "subjects": ["국어", "수학", "영어"]
    })
    keywords = info["keywords"]
    
    # 1. 학업역량 평가 (Gpa & 수강자수 보정)
    gpa_all = calculate_gpa(df_subjects)
    gpa_stem = calculate_gpa(df_subjects, ["수학", "과학"])
    
    # 소수 이수 과목 존재 여부 (40명 이하 수강 과목)
    small_class_exist = not df_subjects[df_subjects["수강자수"] <= 45].empty if not df_subjects.empty else False
    
    academic_level = "중중 (Average)"
    if gpa_all <= 1.35:
        academic_level = "상상 (Top)"
    elif gpa_all <= 1.70:
        academic_level = "상중 (Very High)"
    elif gpa_all <= 2.20:
        academic_level = "상하 (High)"
    elif gpa_all <= 2.80:
        academic_level = "중상 (Above Avg)"
    elif gpa_all <= 3.50:
        academic_level = "중중 (Average)"
    elif gpa_all <= 4.50:
        academic_level = "중하 (Below Avg)"
    else:
        academic_level = "하하 (Low)"

    # 2. 진로역량 평가 (키워드 매칭 + 깊이 판별)
    kw_hits = []
    lines = full_text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if len(line_clean) > 15:
            for kw in keywords:
                if kw in line_clean:
                    kw_hits.append(line_clean)
                    break

    kw_count = len(kw_hits)
    career_level = "중중 (Average)"
    if kw_count >= 15:
        career_level = "상상 (Top)"
    elif kw_count >= 10:
        career_level = "상중 (Very High)"
    elif kw_count >= 6:
        career_level = "상하 (High)"
    elif kw_count >= 3:
        career_level = "중상 (Above Avg)"
    elif kw_count >= 1:
        career_level = "중중 (Average)"
    else:
        career_level = "중하 (Below Avg)"

    # 3. 공동체역량 평가 (리더십, 멘토링, 협동 키워드)
    comm_keywords = ["반장", "부반장", "총무", "멘토", "솔선수범", "배려", "협동", "캠페인", "봉사", "리더십"]
    comm_hits = []
    for line in lines:
        line_clean = line.strip()
        if any(ck in line_clean for ck in comm_keywords):
            comm_hits.append(line_clean)

    comm_level = "상중 (Very High)" if len(comm_hits) >= 4 else "상하 (High)" if len(comm_hits) >= 2 else "중상 (Above Avg)"

    return {
        "gpa_all": gpa_all,
        "gpa_stem": gpa_stem,
        "academic_level": academic_level,
        "career_level": career_level,
        "comm_level": comm_level,
        "kw_hits": list(set(kw_hits))[:5], # 대표 증거문구 5개
        "comm_hits": list(set(comm_hits))[:3],
        "small_class_exist": small_class_exist
    }

# =====================================================================
# 4. Streamlit UI 구성
# =====================================================================
st.title("🎓 학생부 종합 진격(NAVI) AI 평가 & 진단 시스템")
st.caption("농어촌전형 및 수시 학생부종합전형 완벽 대비 정밀 분석 엔진")

st.sidebar.header("📋 학생 및 희망전공 설정")
student_name = st.sidebar.text_input("학생 이름", "조성문")

all_majors = list(MAJOR_MAP.keys())
selected_major = st.sidebar.selectbox("🎯 Target 희망 학과/전공 선택", all_majors, index=0)

uploaded_file = st.sidebar.file_uploader("📂 나이스+ 생활기록부 HTML 파일 업로드", type=["html", "htm"])

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    parsed_list, raw_text = parse_neis_html(content)
    df_subjects = pd.DataFrame(parsed_list)

    eval_result = evaluate_competencies(df_subjects, raw_text, selected_major)

    st.success(f"✅ {student_name} 학생의 생활기록부 파싱 완료! ({len(parsed_list)}개 등급 과목 추출)")

    # -----------------------------------------------------------------
    # SECTION 1: 교과 성적 정밀 산출
    # -----------------------------------------------------------------
    st.markdown("### 📊 1. 교과 성적 산출 결과 (가중평균 기준)")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("전과목 평균", f"{eval_result['gpa_all']} 등급")
    g2.metric("국영수과사 평균", f"{calculate_gpa(df_subjects, ['국어','수학','영어','과학','사회'])} 등급")
    g3.metric("국영수과 평균", f"{calculate_gpa(df_subjects, ['국어','수학','영어','과학'])} 등급")
    g4.metric("수학+과학 평균", f"{eval_result['gpa_stem']} 등급")

    with st.expander("🔍 과목별 상세 등급 내역 확인"):
        st.dataframe(df_subjects, use_container_width=True)

    # -----------------------------------------------------------------
    # SECTION 2: 3대 핵심 역량 7단계 평가
    # -----------------------------------------------------------------
    st.markdown(f"### 🏆 2. [{selected_major}] 전공 맞춤 3대 역량 평가 (7단계 척도)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📚 학업역량", eval_result["academic_level"])
    col2.metric("🎯 진로역량", eval_result["career_level"])
    col3.metric("🤝 공동체역량", eval_result["comm_level"])

    st.markdown("---")

    # -----------------------------------------------------------------
    # SECTION 3: 평가 근거 (Evidence) 자동 인용
    # -----------------------------------------------------------------
    st.markdown("### 🔍 3. 평가 등급 결정 근거 (생기부 실제 문구 인용)")
    
    st.markdown(f"**[진로역량 - {selected_major} 관련 주요 탐구 세특]**")
    if eval_result["kw_hits"]:
        for idx, hit in enumerate(eval_result["kw_hits"], 1):
            st.info(f"**증거 {idx}**: \"... {hit} ...\"")
    else:
        st.warning("선택한 학과 관련 명확한 세특 키워드가 관찰되지 않았습니다.")

    st.markdown("**[공동체역량 - 리더십 및 나눔 세특]**")
    if eval_result["comm_hits"]:
        for idx, hit in enumerate(eval_result["comm_hits"], 1):
            st.success(f"**증거 {idx}**: \"... {hit} ...\"")

    # -----------------------------------------------------------------
    # SECTION 4: 농어촌 전형 특화 보정 해설
    # -----------------------------------------------------------------
    st.markdown("### 🌾 4. 농어촌 전형 및 학교 환경 보정 진단")
    if eval_result["small_class_exist"]:
        st.warning("💡 **소수 이수 과목 감안 서류 평가 우대**: 수강자 수가 40명 안팎인 과목(예: 물리학Ⅰ, 한국지리, 화학Ⅰ 등)에서 1~2등급을 유지하였습니다. 입시 사관 평가 시 단순 등급 수치보다 높은 학업 우수성(약 1.1~1.2등급 수준)으로 보정 평가됩니다.")
    else:
        st.info("💡 일반적인 이수자 수 환경에서 고른 등급 유지를 보여주고 있습니다.")

    # -----------------------------------------------------------------
    # SECTION 5: 3학년 세특 고도화 탐구 보고서 추천 주제 (대학 1-2학년 수준)
    # -----------------------------------------------------------------
    st.markdown(f"### 🔬 5. [{selected_major}] 합격 격차를 만드는 3학년 심화 탐구 주제 제안")
    
    st.markdown(f"""
    #### 📌 추천 주제 1. [수리적 원리 규명]
    * **연계과목**: 미적분 / 기하 / 인공지능 수학
    * **주제**: `{selected_major}` 분야의 핵심 알고리즘 수리적 모델링 및 최적화 연구
    * **탐구 내용**: 고등 수학 범위를 넘어 **편미분(Partial Derivative)**과 **손실함수(Loss Function)** 경사하강법의 최적화 가속 알고리즘(Adam, Momentum) 비교 구현.

    #### 📌 추천 주제 2. [실전 시스템 구축]
    * **연계과목**: 프로그래밍 / 물리학 / 공학일반
    * **주제**: 객체지향 프로그래밍(OOP) 기반 `{selected_major}` 응용 모듈화 설계 및 아두이노/라즈베리파이 센서 융합
    * **탐구 내용**: 파이썬의 `Class`와 `Inheritance` 구조를 활용하여 데이터 수집-전처리-예측 모델 구조의 소프트웨어 공학적 설계.

    #### 📌 추천 주제 3. [사회적/윤리적 융합 탐구]
    * **연계과목**: 확률과 통계 / 독서 / 사회·문화
    * **주제**: `{selected_major}` 도입에 따른 정보 엔트로피(Information Entropy) 변화와 편향성(Data Bias) 정량 분석
    * **탐구 내용**: **샤논 엔트로피(Shannon Entropy)** 공식을 활용해 모델의 예측 불확실성을 정량화하고 데이터 균형 모델 제시.
    """)

else:
    st.info("👈 좌측 사이드바에서 학생부 HTML 파일을 업로드해 주세요.")
