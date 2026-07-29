import streamlit as st
import os

# ---------------------------------------------------------------------------
# 1. 페이지 기본 설정 (반드시 코드 최상단에 위치해야 합니다)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="천명의선택 학생부 NAVI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 2. 커스텀 CSS (디자인 및 스타일링)
# ---------------------------------------------------------------------------
st.markdown("""
    <style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
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
    .result-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. 사이드바 - API 키 입력 및 설정
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/illustrations/100/compass.png", width=80)
    st.title("🧭 설정 & API")
    
    # Secrets 또는 직접 입력 방식 지원
    api_key = st.text_input(
        "OpenAI API Key 입력", 
        value=st.secrets.get("OPENAI_API_KEY", ""), 
        type="password",
        help="sk-... 로 시작하는 OpenAI API 키를 입력하세요."
    )
    
    model_choice = st.selectbox(
        "사용할 AI 모델 선택",
        ["gpt-4o", "gpt-4o-mini"],
        index=0
    )
    
    st.divider()
    st.markdown("### 📌 사용 가이드")
    st.caption("1. 학생의 계열/진로 및 희망 대학/학과를 입력하세요.")
    st.caption("2. 세부능력 및 특기사항(세특) 내용 또는 탐구 주제를 작성합니다.")
    st.caption("3. [분석 및 컨설팅 생성] 버튼을 누르면 입시 전문 분석 보고서가 생성됩니다.")

# ---------------------------------------------------------------------------
# 4. 메인 화면 헤더
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">🧭 천명의선택 학생부 NAVI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">학생부 종합전형 & 농어촌 전형 맞춤형 교과세특·탐구활동 AI 컨설팅 시스템</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 5. 입력 폼 구성
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    target_major = st.text_input("🎯 희망 전공/학과", placeholder="예: 약학과, 인공지능공학과, 미디어커뮤니케이션학과")
    student_grade = st.selectbox("🎓 학년", ["고등학교 1학년", "고등학교 2학년", "고등학교 3학년"])

with col2:
    admission_type = st.selectbox("📋 주력 전형", ["일반전형 (학생부종합)", "농어촌 특별전형 (학생부종합)", "학생부교과전형", "기타"])
    subject_name = st.text_input("📚 대상 과목명", placeholder="예: 생명과학Ⅰ, 수학Ⅱ, 사회·문화")

st.markdown("---")

inquiry_topic = st.text_input("💡 기존 탐구 주제 / 관심 키워드", placeholder="예: 슬라임곰팡이(Physarum polycephalum)를 활용한 도시 교통망 최적화")
record_text = st.text_area("📝 현재 세특 내용 또는 세부 활동 설명 (선택사항)", height=150, placeholder="학생부에 작성되었거나 구상 중인 탐구 활동 내용을 입력하세요.")

# ---------------------------------------------------------------------------
# 6. AI 연동 및 로직 처리 함수
# ---------------------------------------------------------------------------
def generate_consulting(api_key, model_name, major, grade, adm_type, subject, topic, record):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        system_prompt = """
당신은 대한민국 최고 수준의 대입 입시 컨설팅 전문가이자 학생부 종합전형/농어촌전형 평가위원입니다.
학생의 학년, 희망 전공, 대상 과목, 탐구 주제를 분석하여 학술적 깊이(고등 최상위 ~ 대학교 1-2학년 수준)와
타당성을 갖춘 세부능력 및 특기사항(교과세특) 탐구 보고서 가이드를 작성해야 합니다.

답변은 다음 구성을 엄격히 지켜 명확하고 체계적으로 작성하세요:
1. 🎯 **전공 연계성 및 평가 포인트 분석** (해당 전형 및 전공 관점)
2. 🔬 **심화 탐구 주제 제안 (2~3가지)**
3. 📖 **추천 탐구 활동 & 학술적 이론/근거** (학술적 메커니즘 포함)
4. 📝 **교과세특 세부 작성 예시문 (500자~700자 내외)**
"""

        user_prompt = f"""
[학생 정보]
- 학년: {grade}
- 희망 전공: {major}
- 전형 유형: {adm_type}
- 대상 과목: {subject}
- 현재 탐구 주제/키워드: {topic}
- 기존 내용/메모: {record}

위 정보를 바탕으로 학생부 종합 경쟁력을 극대화할 수 있는 세특 컨설팅 보고서를 작성해 주세요.
"""

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"

# ---------------------------------------------------------------------------
# 7. 실행 및 결과 출력
# ---------------------------------------------------------------------------
if st.button("🚀 분석 및 컨설팅 생성", use_container_width=True):
    if not api_key:
        st.error("⚠️ OpenAI API Key가 입력되지 않았습니다. 왼쪽 사이드바에 API 키를 입력해 주세요.")
    elif not target_major or not subject_name:
        st.warning("⚠️ 희망 전공과 대상 과목명은 필수 입력 항목입니다.")
    else:
        with st.spinner("전문가 관점에서 학술 자료 및 입시 데이터를 분석 중입니다..."):
            result = generate_consulting(
                api_key=api_key,
                model_name=model_choice,
                major=target_major,
                grade=student_grade,
                adm_type=admission_type,
                subject=subject_name,
                topic=inquiry_topic,
                record=record_text
            )
            
            if result.startswith("Error:"):
                st.error(f"❌ 분석 실패: {result}")
            else:
                st.success("✅ 컨설팅 보고서가 성공적으로 생성되었습니다!")
                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.markdown(result)
                st.markdown('</div>', unsafe_allow_html=True)
