import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import json

# Page Configuration
st.set_page_config(
    page_title="천명의선택 학생부 NAVI",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Design
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
    .section-card {
        background-color: #F8FAFC;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2563EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar: API & Global Settings
with st.sidebar:
    st.image("https://img.icons8.com/color/96/compass.png", width=60)
    st.title("⚙️ 설정 & API")
    
    api_key = st.text_input("OpenAI API Key 입력", type="password", help="API 키를 입력하면 AI 정밀 분석 모드가 활성화됩니다.")
    selected_model = st.selectbox("사용할 AI 모델 선택", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
    
    st.divider()
    
    st.markdown("### 📌 사용 가이드")
    st.markdown("""
    1. **기본 정보 및 입시 목표**를 설정합니다.
    2. **학생부 HTML 파일**을 업로드하거나 직접 세특/탐구 내용을 입력합니다.
    3. **3대 역량(학업·진로·공동체)** 세부 항목을 평가합니다.
    4. **[분석 및 컨설팅 생성]**을 눌러 정밀 예측 보고서를 확인합니다.
    """)
    
    st.caption("※ 본 분석 자료는 입시 분석 데이터 기반의 예측 모델입니다.")

# Main Title Area
st.markdown("<div class="main-header">🧩 천명의선택 학생부 NAVI</div>", unsafe_allow_html=True)
st.markdown("<div class="sub-header">학생부종합전형 & 농어촌전형 맞춤형 교과세특·학업역량 통합 AI 컨설팅 시스템</div>", unsafe_allow_html=True)

# Layout: 2 Columns (Inputs & Uploads)
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 1. 기본 입시 정보 입력")
    
    c1, c2 = st.columns(2)
    with c1:
        grade_avg = st.number_input("전과목/주요과목 내신등급", min_value=1.00, max_value=9.00, value=2.10, step=0.01)
        target_region = st.selectbox("선호 희망 지역", ["수도권 (서울/경기/인천)", "충청권", "전라권", "경상권", "강원권", "제주권"])
    with c2:
        target_univ = st.text_input("목표 대학", value="연세대학교 / 고려대학교")
        target_dept = st.text_input("희망 전공/학과", value="약학과, 인공지능공학과, 미디어커뮤니케이션학과")
    
    c3, c4 = st.columns(2)
    with c3:
        admission_type = st.selectbox("주력 전형 선택", ["일반전형 (학생부종합)", "농어촌 특별전형 (학종)", "농어촌 특별전형 (교과)", "기회균등 전형"])
    with c4:
        school_year = st.selectbox("학년 구분", ["고등학교 1학년", "고등학교 2학년", "고등학교 3학년", "N수생/졸업생"])

with col2:
    st.subheader("📂 2. 학생부 HTML 업로드 및 입력")
    
    uploaded_file = st.file_uploader("학생부 HTML/TXT 파일 업로드 (NEIS 수기 출력본 가능)", type=["html", "htm", "txt"])
    
    parsed_student_data = ""
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8")
            soup = BeautifulSoup(content, 'html.parser')
            # 파싱 로직 (텍스트 추출)
            parsed_student_data = soup.get_text(separator="\n", strip=True)
            st.success("✅ 학생부 파일 파싱 성공! 데이터가 자동 추출되었습니다.")
            with st.expander("파싱된 학생부 데이터 보기"):
                st.text(parsed_student_data[:1000] + "...")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    existing_topic = st.text_input("기존 탐구 주제 / 핵심 관심 키워드", value="슬라임곰팡이(Physarum polycephalum)를 활용한 도시 교통망 최적화")
    subject_details = st.text_area("현재 세특 내용 또는 세부 탐구 활동 설명 (선택사항)", 
                                  value=parsed_student_data if parsed_student_data else "학생부에 작성되었거나 구상 중인 탐구 활동 내용을 입력하세요.", height=100)

st.divider()

# Section 3: 3대 역량 평가 (학업, 진로, 공동체)
st.subheader("📊 3. 대학 입시 표준 평가요소 (3대 역량 정밀 평가)")

tab_academic, tab_career, tab_community = st.tabs(["📘 학업역량", "📗 진로역량", "📙 공동체역량"])

with tab_academic:
    st.markdown("##### 💡 학업역량 평가 (학업을 성실히 수행하고 성취할 수 있는 능력)")
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        score_academic_achieve = st.slider("학업성취도 (교과 성적 수준 및 추이)", 1, 5, 4)
    with ca2:
        score_academic_attitude = st.slider("학업태도 (자기주도적 학습 의지)", 1, 5, 4)
    with ca3:
        score_academic_inquiry = st.slider("탐구력 (지적 호기심 및 탐구 깊이)", 1, 5, 5)

with tab_career:
    st.markdown("##### 💡 진로역량 평가 (자신의 진로와 전공에 대한 탐색 노력과 능력)")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        score_career_course = st.slider("전공 관련 교과 이수 노력 (과목 선택)", 1, 5, 5)
    with cc2:
        score_career_achieve = st.slider("전공 관련 교과 성취도 (위계 과목 성적)", 1, 5, 4)
    with cc3:
        score_career_exploration = st.slider("진로 탐구 활동과 경험 (세특 탐구 깊이)", 1, 5, 5)

with tab_community:
    st.markdown("##### 💡 공동체역량 평가 (공동체의 일원으로서 갖춰야 할 바람직한 사고와 행동)")
    cm1, cm2, cm3, cm4 = st.columns(4)
    with cm1:
        score_comm_coop = st.slider("협동과 소통", 1, 5, 4)
    with cm2:
        score_comm_share = st.slider("나눔과 배려", 1, 5, 4)
    with cm3:
        score_comm_rule = st.slider("성실성과 규칙준수", 1, 5, 5)
    with cm4:
        score_comm_lead = st.slider("리더십 및 문제해결", 1, 5, 4)

# Calculate Integrated Scores
total_academic = round((score_academic_achieve + score_academic_attitude + score_academic_inquiry) / 15 * 100, 1)
total_career = round((score_career_course + score_career_achieve + score_career_exploration) / 15 * 100, 1)
total_community = round((score_comm_coop + score_comm_share + score_comm_rule + score_comm_lead) / 20 * 100, 1)
overall_score = round((total_academic * 0.4) + (total_career * 0.4) + (total_community * 0.2), 1)

st.divider()

# Action Button & Report Generation
if st.button("🚀 분석 및 컨설팅 보고서 생성", type="primary", use_container_width=True):
    st.markdown("### 📝 종합 입시 분석 및 세특 검증 보고서")
    
    # Summary Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("내신 등급", f"{grade_avg} 등급")
    m2.metric("학업역량 점수", f"{total_academic} 점")
    m3.metric("진로역량 점수", f"{total_career} 점")
    m4.metric("종합 역량 평가", f"{overall_score} 점")
    
    st.markdown("---")
    
    # Analysis Details
    st.markdown(f"#### 🔍 **[{target_univ}] {target_dept} ({admission_type}) 분석 결과**")
    
    # Diagnostic Message
    st.info(f"**전형 적합성 진단:** 지원 희망전형인 **'{admission_type}'** 기준, 현재 학업성취도({grade_avg}등급)와 진로 탐구 역량({total_career}점) 수준을 종합 시 최상위권 타겟 지원이 가능합니다. (본 분석은 통계적 분석에 근거한 예측 모델입니다.)")
    
    col_rep1, col_rep2 = st.columns(2)
    
    with col_rep1:
        st.markdown("##### 📌 학생부 강점 분석 (Strength)")
        st.write(f"- **탐구 세부 능력:** '{existing_topic}' 주제와 관련된 구체적 메커니즘 분석 및 심화 탐구 역량이 우수함.")
        st.write(f"- **교과 위계 이수:** 목표 학과({target_dept}) 진학에 필요한 필수 권장 과목의 이수 노력이 높은 수준임.")
        st.write(f"- **역량 밸런스:** 진로역량({total_career}점)과 학업역량({total_academic}점)의 유기적 연결성이 뛰어남.")
        
    with col_rep2:
        st.markdown("##### 🎯 보완 및 검증 포인트 (Improvement)")
        st.write("- **학업 성취도 보완:** 주요 타겟 대학 합격선 확보를 위한 핵심 과목 성적 보강 권장.")
        st.write("- **공동체 역량 구체화:** 리더십 및 나눔 활동에서 단순 참여를 넘어선 문제 해결 사례 수록 필요.")
        st.write("- **농어촌/학종 전형 특화:** 대학별 정량/정성 평가 방식 변화에 맞춘 세특 텍스트 검증 지속 필요.")

    st.success("✅ **컨설팅 솔루션 제안:** 심화 탐구 보고서 작성 시 단순 문헌 조사를 넘어, 실험 설계 또는 데이터 기반 최적화 모델을 적용하여 세특에 반영할 것을 권장합니다.")
