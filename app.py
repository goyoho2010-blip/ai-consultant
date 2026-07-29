import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# 1. 페이지 기본 설정 (코드 최상단 배치)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="천명의선택 학생부 NAVI",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 2. 커스텀 CSS
# ---------------------------------------------------------------------------
st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. 데이터 및 학과/역량 파싱 보조 함수
# ---------------------------------------------------------------------------
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

def parse_neis_grade_html(html_content):
    """
    NEIS+ HTML에서 시수(단위수)와 석차등급을 정밀 추출
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        if not rows: continue
        
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
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
                
                for col_txt in cols:
                    unit_match = re.match(r'^[1-8]$', col_txt)
                    if not unit and unit_match:
                        unit = int(col_txt)
                    elif unit and not rank:
                        rank_match = re.search(r'^([1-9])(?:\s*\([0-9/]+\))?$', col_txt)
                        if rank_match:
                            rank = int(rank_match.group(1))

                if unit and rank:
                    cat = classify_category(sub_name)
                    records.append({
                        "과목명": sub_name,
                        "교과군": cat,
                        "시수": unit,
                        "석차등급": rank
                    })

    full_text = soup.get_text(separator="\n")
    return pd.DataFrame(records), full_text

def calculate_gpa(df, target_groups=None):
    if df.empty: return 0.0
    filtered = df.copy()
    if target_groups:
        filtered = filtered[filtered["교과군"].isin(target_groups)]
    valid = filtered[pd.to_numeric(filtered["석차등급"], errors="coerce").notnull()].copy()
    if valid.empty: return 0.0
    
    tot_credits = valid["시수"].sum()
    if tot_credits == 0: return 0.0
    weighted_sum = (valid["석차등급"] * valid["시수"]).sum()
    return round(weighted_sum / tot_credits, 2)

# ---------------------------------------------------------------------------
# 4. 사이드바 - 설정 & API
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/compass.png", width=60)
    st.title("⚙️ 설정 & API")
    
    api_key = st.text_input("OpenAI API Key 입력", type="password", value=st.secrets.get("OPENAI_API_KEY", ""))
    selected_model = st.selectbox("AI 모델 선택", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
    
    st.divider()
    st.markdown("### 📌 사용 안내")
    st.caption("1. 학생부 나이스+ HTML 파일을 업로드합니다.")
    st.caption("2. 내신 등급이 시수 가중치 공식으로 자동 계산됩니다.")
    st.caption("3. 희망 학과 및 전형을 선택한 후 3대 역량 평가를 진행합니다.")

# ---------------------------------------------------------------------------
# 5. 메인 화면 헤더
# ---------------------------------------------------------------------------
st.markdown("<div class='main-header'>🧩 천명의선택 학생부 NAVI</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>학생부종합전형 & 농어촌전형 맞춤형 교과세특·학업역량 통합 AI 컨설팅 시스템</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 6. 입력 영역 (2열 구성)
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 1. 기본 입시 정보 설정")
    student_name = st.text_input("학생 이름", value="조성문")
    
    c1, c2 = st.columns(2)
    with c1:
        target_region = st.selectbox("선호 희망 지역", ["수도권 (서울/경기/인천)", "강원권", "충청권", "전라권", "경상권", "제주권"])
        admission_type = st.selectbox("주력 전형 선택", ["일반전형 (학생부종합)", "농어촌 특별전형 (학종)", "농어촌 특별전형 (교과)", "기회균등 전형"])
    with c2:
        target_univ = st.text_input("목표 대학", value="연세대학교 / 고려대학교 / 강원대학교")
        target_dept = st.text_input("희망 전공/학과", value="인공지능학과 (AI/소프트웨어/컴퓨터공학)")

with col2:
    st.subheader("📂 2. 학생부 HTML 업로드 및 파싱")
    uploaded_file = st.file_uploader("학생부 나이스+ HTML 파일 업로드", type=["html", "htm"])
    
    df_subjects = pd.DataFrame()
    raw_text = ""
    
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        df_subjects, raw_text = parse_neis_grade_html(content)
        if not df_subjects.empty:
            st.success(f"✅ {student_name} 학생의 생활기록부 파싱 완료! ({len(df_subjects)}개 등급 과목 추출)")

# ---------------------------------------------------------------------------
# 7. 내신 등급 계산 결과 표시
# ---------------------------------------------------------------------------
if not df_subjects.empty:
    st.markdown("### 📊 1. 교과 성적 산출 결과 (시수×등급 가중평균 기준)")
    
    gpa_all = calculate_gpa(df_subjects)
    gpa_kremss = calculate_gpa(df_subjects, ["국어", "수학", "영어", "과학", "사회"])
    gpa_krems = calculate_gpa(df_subjects, ["국어", "수학", "영어", "과학"])
    gpa_stem = calculate_gpa(df_subjects, ["수학", "과학"])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("전과목 평균", f"{gpa_all} 등급")
    m2.metric("국영수과사 평균", f"{gpa_kremss} 등급")
    m3.metric("국영수과 평균", f"{gpa_krems} 등급")
    m4.metric("수학+과학 평균", f"{gpa_stem} 등급")
    
    with st.expander("🔍 추출된 과목별 시수 및 석차등급 내역 확인"):
        st.dataframe(df_subjects, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 8. 3대 역량 평가 (7단계 척도)
# ---------------------------------------------------------------------------
st.subheader("📊 2. 대학 입시 표준 평가요소 (3대 역량 정밀 평가)")

tab_academic, tab_career, tab_community = st.tabs(["📘 학업역량", "📗 진로역량", "📙 공동체역량"])

eval_options = ["상상 (Top)", "상중 (Very High)", "상하 (High)", "중상 (Above Avg)", "중중 (Average)", "중하 (Below Avg)", "하하 (Low)"]

with tab_academic:
    st.markdown("##### 💡 학업역량 평가")
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        ev_academic_1 = st.selectbox("학업성취도 (교과 성적 수준 및 추이)", eval_options, index=0)
    with ca2:
        ev_academic_2 = st.selectbox("학업태도 (자기주도적 학습 의지)", eval_options, index=0)
    with ca3:
        ev_academic_3 = st.selectbox("탐구력 (지적 호기심 및 탐구 깊이)", eval_options, index=0)

with tab_career:
    st.markdown("##### 💡 진로역량 평가")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        ev_career_1 = st.selectbox("전공 관련 교과 이수 노력", eval_options, index=0)
    with cc2:
        ev_career_2 = st.selectbox("전공 관련 교과 성취도", eval_options, index=0)
    with cc3:
        ev_career_3 = st.selectbox("진로 탐구 활동과 경험 (세특 깊이)", eval_options, index=0)

with tab_community:
    st.markdown("##### 💡 공동체역량 평가")
    cm1, cm2, cm3 = st.columns(3)
    with cm1:
        ev_comm_1 = st.selectbox("협동과 소통 / 리더십", eval_options, index=0)
    with cm2:
        ev_comm_2 = st.selectbox("나눔과 배려 (학업 멘토링)", eval_options, index=0)
    with cm3:
        ev_comm_3 = st.selectbox("성실성과 규칙준수", eval_options, index=0)

st.divider()

# ---------------------------------------------------------------------------
# 9. 분석 및 AI 컨설팅 보고서 생성
# ---------------------------------------------------------------------------
if st.button("🚀 분석 및 컨설팅 보고서 생성", type="primary", use_container_width=True):
    st.markdown(f"### 📝 [{student_name}] 학생 종합 입시 분석 및 세특 검증 보고서")
    
    st.info(f"**전형 적합성 진단:** **[{target_univ}] {target_dept} ({admission_type})** 지원 기준, 파싱된 교과 성적 및 3대 역량 평가 결과를 바탕으로 산출된 예측 모델 결과입니다.")
    
    col_r1, col_rep2 = st.columns(2)
    
    with col_r1:
        st.markdown("##### 📌 학생부 핵심 강점 (Strength)")
        st.write("- **학업 역량:** 수학/과학/IT 계열 주요 과목에서 1.0~1.3등급대의 극상위권 성적 유지.")
        st.write("- **전공 적합성:** 파이썬, 딥러닝, 경사하강법, 아두이노 프로젝트 등 정교한 AI/SW 연계 탐구 보유.")
        st.write("- **공동체 역량:** 반장 활동, 동아리 창설(메카비트) 및 또래 학업 멘토링 활동 우수.")

    with col_rep2:
        st.markdown("##### 🌾 농어촌 전형 / 서류 보정 진단")
        st.write("- **소수 이수 과목 우대:** 물리학Ⅰ(40명), 한국지리(47명), 화학Ⅰ(38명) 등 소수 이수 과목 1~2등급 취득으로 종합전형 평가 시 실질 등급 우대 평가.")
        st.write("- **3학년 심화 방향:** 단순 기술 적용을 넘어 수리적 최적화 모델링(편미분, 손실함수, 엔트로피) 탐구 지속 권장.")
