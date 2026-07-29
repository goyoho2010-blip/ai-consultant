import os
import math
import re
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

# ==========================================
# 0. 페이지 기본 설정 및 디자인
# ==========================================
st.set_page_config(
    page_title="천명의선택 학생부 NAVI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header { 
        font-size: 2.3rem; 
        font-weight: 800; 
        color: #38BDF8; 
        margin-bottom: 0.3rem; 
        text-shadow: 0px 2px 4px rgba(0,0,0,0.3);
    }
    .sub-header { 
        font-size: 1.05rem; 
        color: #94A3B8; 
        margin-bottom: 1.5rem; 
    }
    .stAlert { border-radius: 8px; }
    .metric-container {
        background-color: #1E293B;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #334155;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. API 키 자동 로드 로직 (구글 Gemini)
# ==========================================
AUTO_GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# ==========================================
# 2. 초기화 상태 관리
# ==========================================
if 'reset_count' not in st.session_state:
    st.session_state.reset_count = 0

def force_reset():
    for key in list(st.session_state.keys()):
        if key != 'reset_count':
            del st.session_state[key]
    st.session_state.reset_count += 1

r_id = st.session_state.reset_count

# ==========================================
# 3. 세분화된 전공 / 학과 리스트 정의
# ==========================================
MAJOR_CATEGORIES = {
    "--- 선택하세요 ---": ["-"],
    "--- 자연과학 / 공학 / 도시 ---": [
        "도시공학과", "건축학과", "건축공학과", "토목공학과", "인공지능학과 / AI학부", 
        "컴퓨터공학과", "소프트웨어전공", "기계공학과", "화학공학과", "신소재공학과"
    ],
    "--- 의약학 / 수의 / 생명 ---": [
        "수의예과", "의예과", "치의예과", "한의예과", "약학과", "간호학과", 
        "생명과학과", "생명공학과", "화공생명공학과", "바이오시스템공학과"
    ],
    "--- 전기 / 전자 / 반도체 ---": [
        "전자공학과", "전기공학과", "반도체공학과", "시스템반도체공학과", "경영공학과", "융합공학과"
    ],
    "--- 인문 / 어학 ---": [
        "국어국문학과", "영어영문학과", "사학과", "철학과", "외국어문학부", "문헌정보학과"
    ],
    "--- 사회 / 상경 / 언론 ---": [
        "심리학과", "경영학과", "경제학과", "사회학과", "정치외교학과", 
        "신문방송학과 / 미디어커뮤니케이션", "행정학과", "사회복지학과"
    ],
    "--- 사범 / 교육 ---": [
        "교육학과", "초등교육과 (교대)", "국어교육과", "영어교육과", "수학교육과", "컴퓨터교육과"
    ],
    "--- 예체능 ---": [
        "디자인학과", "회화과", "음악학과", "체육학과", "연극영화과"
    ]
}

FLAT_MAJOR_LIST = []
for cat, majors in MAJOR_CATEGORIES.items():
    FLAT_MAJOR_LIST.extend(majors)

# ==========================================
# 4. 범용 NEIS HTML 파서 엔진
# ==========================================
class NEISParserAndEngine:
    @staticmethod
    def parse_neis_html(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        subjects_data = []
        parsed_name = ""

        for tag in soup.find_all(['td', 'th', 'span', 'div', 'p']):
            txt = tag.get_text(strip=True)
            m = re.search(r'성\s*명\s*[:：]\s*([가-힣]{2,5})', txt)
            if m:
                parsed_name = m.group(1)
                break
            m2 = re.search(r'([가-힣]{2,5})\s*님', txt)
            if m2 and m2.group(1) not in ['선생', '관리자', '사용자']:
                parsed_name = m2.group(1)
                break

        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if not rows:
                continue

            unit_idx = -1
            rank_idx = -1
            sub_idx = -1

            for r in rows:
                header_cols = [td.get_text(strip=True).replace(" ", "") for td in r.find_all(['td', 'th'])]
                for i, c in enumerate(header_cols):
                    if ('과목' in c or '교과' in c) and sub_idx == -1:
                        sub_idx = i
                    elif '단위' in c:
                        unit_idx = i
                    elif '석차' in c or '등급' in c:
                        rank_idx = i

            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cols) < 4:
                    continue

                row_str = " ".join(cols)
                if '원점수' in row_str or '과목' in row_str or '석차등급' in row_str or '단위수' in row_str:
                    continue

                sub_name = ""
                unit = None
                rank = None

                if sub_idx >= 0 and sub_idx < len(cols):
                    sub_name = cols[sub_idx]
                if unit_idx >= 0 and unit_idx < len(cols):
                    if re.match(r'^[1-8]$', cols[unit_idx]):
                        unit = float(cols[unit_idx])
                if rank_idx >= 0 and rank_idx < len(cols):
                    m_rank = re.search(r'^\s*([1-9])\s*(?:\(\s*\d+\s*\))?\s*$', cols[rank_idx])
                    if m_rank:
                        rank = float(m_rank.group(1))

                if unit is None or rank is None or not sub_name:
                    for col in cols:
                        if not sub_name and re.search(r'[가-힣]{2,}', col):
                            if not any(k in col for k in ['학기', '학년', '수강', '이수', '성취', '원점수', '평균', '공통', '일반']):
                                sub_name = col
                        if unit is None and re.match(r'^[1-8]$', col):
                            unit = float(col)
                        m_r = re.search(r'^\s*([1-9])\s*(?:\(\s*\d+\s*\))?\s*$', col)
                        if m_r and unit is not None and col != str(int(unit)):
                            rank = float(m_r.group(1))

                if sub_name and unit is not None and rank is not None:
                    if not any(ex in sub_name for ex in ['체육', '음악', '미술', '운동', '스포츠', '진로', '교양', '군']):
                        is_core = not any(ex in sub_name for ex in ['정보', '컴퓨터', '제2외국어', '한문', '보건', '환경', '교양'])
                        subjects_data.append({
                            'subject': sub_name,
                            'unit': unit,
                            'grade': rank,
                            'is_core': is_core
                        })

        seteuk_dict = {}
        sections = soup.find_all(['p', 'div', 'td', 'span'])
        for sec in sections:
            txt = sec.get_text(strip=True)
            if len(txt) > 40 and "세부능력" not in txt and "학교생활기록" not in txt:
                seteuk_dict["교과탐구"] = seteuk_dict.get("교과탐구", "") + " " + txt

        return {"student_name": parsed_name, "scores": subjects_data, "seteuk": seteuk_dict}

    @staticmethod
    def calculate_gpas_professional(score_info):
        if not score_info:
            return 0.0, 0.0
            
        df = pd.DataFrame(score_info)
        df = df[df['grade'].between(1, 9)].drop_duplicates()
        
        if df.empty:
            return 0.0, 0.0

        tot_units = df['unit'].sum()
        if tot_units == 0:
            return 0.0, 0.0
        weighted_sum = (df['grade'] * df['unit']).sum()
        gpa_all = round(weighted_sum / tot_units, 2)

        core_df = df[df['is_core'] == True]
        if core_df.empty:
            gpa_core = gpa_all
        else:
            core_units = core_df['unit'].sum()
            if core_units == 0:
                gpa_core = gpa_all
            else:
                core_weighted = (core_df['grade'] * core_df['unit']).sum()
                gpa_core = round(core_weighted / core_units, 2)

        return gpa_all, gpa_core

# ==========================================
# 5. 사이드바 UI (브라우저 자동완성 차단 추가)
# ==========================================
with st.sidebar:
    st.header("⚙️ 분석 설정 및 데이터 입력")
    
    st.button("🔄 전체 데이터 초기화", on_click=force_reset, use_container_width=True, type="secondary", key=f"btn_reset_side_{r_id}")

    st.markdown("---")
    
    # HTML 속성 주입을 통한 브라우저 자동완성 원천 차단
    st.markdown("""
    <script>
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        inputs.forEach(input => input.setAttribute('autocomplete', 'off'));
    </script>
    """, unsafe_allow_html=True)

    student_name_input = st.text_input("학생 이름", value="", placeholder="학생 이름을 입력하세요", key=f"name_{r_id}")
    
    if AUTO_GEMINI_API_KEY:
        st.success("🤖 Gemini AI API 키가 시스템에 자동 연동되었습니다.")
        api_key_input = AUTO_GEMINI_API_KEY
    else:
        api_key_input = st.text_input("Gemini API Key 입력", type="password", key=f"key_{r_id}", help="자동 설정된 키가 없을 경우 수동 입력")

    uploaded_file = st.file_uploader("NEIS 성적/세특 HTML 파일 업로드", type=["html", "htm"], key=f"file_{r_id}")
    
    if uploaded_file is not None:
        html_content = uploaded_file.read().decode('utf-8', errors='ignore')
        parsed_data = NEISParserAndEngine.parse_neis_html(html_content)
        
        if student_name_input.strip():
            display_student = student_name_input.strip()
        elif parsed_data["student_name"]:
            display_student = parsed_data["student_name"]
        else:
            display_student = "학생"
            
        st.success(f"✅ {display_student} 학생 파일 파싱 완료")
        gpa_all_calc, gpa_core_calc = NEISParserAndEngine.calculate_gpas_professional(parsed_data['scores'])
    else:
        parsed_data = {"student_name": "", "scores": [], "seteuk": {}}
        gpa_all_calc, gpa_core_calc = 0.0, 0.0
        display_student = student_name_input.strip() if student_name_input.strip() else "미입력"

    if 'selected_gpa' not in st.session_state:
        st.session_state.selected_gpa = gpa_all_calc if gpa_all_calc > 0 else 0.0
    if 'selected_label' not in st.session_state:
        st.session_state.selected_label = "미선택"

    all_text = " ".join(parsed_data['seteuk'].values()) if parsed_data['seteuk'] else ""
    if uploaded_file is not None and st.session_state.selected_gpa > 0 and st.session_state.selected_label != "미선택":
        curr_gpa = st.session_state.selected_gpa
        eval_academic = "중상 (Above Avg)" if curr_gpa >= 3.0 else "상상 (Top)" if curr_gpa <= 1.70 else "상중 (Very High)"
        eval_career = "상상 (Top)" if any(k in all_text for k in ["도시", "건축", "공학", "설계", "공간", "지리", "환경"]) else "상중 (Very High)"
        eval_comm = "상상 (Top)"
    else:
        eval_academic = "-"
        eval_career = "-"
        eval_comm = "-"

    st.markdown("---")
    st.markdown("### 📌 파싱 산출 내신 요약")
    if uploaded_file is not None and gpa_all_calc > 0:
        st.write(f"- **전과목 평균**: {gpa_all_calc:.2f} 등급")
        st.write(f"- **국영수과사 평균**: {gpa_core_calc:.2f} 등급")
    else:
        st.write("- **전과목 평균**: 0.00 등급")
        st.write("- **국영수과사 평균**: 0.00 등급")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 3대 역량 세특 정밀 분석")
    st.write(f"- **학업**: [ {eval_academic} ]")
    st.write(f"- **진로**: [ {eval_career} ]")
    st.write(f"- **공동체**: [ {eval_comm} ]")

# ==========================================
# 6. 메인 화면 UI
# ==========================================

st.markdown('<div class="main-header">🧭 천명의선택 학생부 NAVI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">NEIS 정밀 분석 | 전형별 맞춤 산출 | 3대 역량 세특 진단 | 입결 예측 엔진</div>', unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    st.button("🔄 메인 설정 및 평가 초기화", on_click=force_reset, use_container_width=True, type="secondary", key=f"btn_reset_main_{r_id}")

st.markdown("<br>", unsafe_allow_html=True)

col_top1, col_top2 = st.columns(2)

with col_top1:
    selected_major = st.selectbox("🎯 희망 전공/학과 선택", FLAT_MAJOR_LIST, index=0, key=f"major_{r_id}")

with col_top2:
    admission_mode = st.selectbox(
        "📋 주력 전형 선택",
        ["일반전형 (학생부종합/교과)", "농어촌 특별전형 (학생부종합/교과)"],
        index=0,
        key=f"admission_{r_id}"
    )

is_rural = "농어촌" in admission_mode

if selected_major != "-" and admission_mode != "-":
    if is_rural:
        st.info("🌾 **농어촌 특별전형 알고리즘 적용 중**: 소수 이수 과목 우대 및 농어촌 전용 입결 기준 반영")
    else:
        st.info("🏛️ **일반전형 분석 알고리즘 적용 중**: 정규 Z-Score 및 통상 학종/교과 입결 기준 반영")

st.divider()

tab1, tab2, tab3 = st.tabs([
    "📊 ① 교과 성적 기준 등급 선택", 
    "📝 ② 3대 역량 세특 정밀 분석", 
    f"🎯 ③ [{display_student}] 학생부 종합 입시 분석"
])

# ------------------------------------------
# TAB 1: 교과 성적 기준 등급 선택
# ------------------------------------------
with tab1:
    st.subheader("📊 교과 성적 산출 및 기준 등급 확정")
    st.caption("아래 3가지 항목 중 원하는 등급의 **[확인]** 단추를 누르면, 해당 등급이 전체 입시 분석의 기준 등급으로 확정됩니다.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown("### 1) 전과목")
        if gpa_all_calc > 0:
            st.markdown(f"# **{gpa_all_calc:.2f}** <span style='font-size:1.2rem;'>등급</span>", unsafe_allow_html=True)
        else:
            st.markdown("# **0.00** <span style='font-size:1.2rem;'>등급</span>", unsafe_allow_html=True)
            
        if st.button("확인", key=f"btn_all_{r_id}", use_container_width=True):
            st.session_state.selected_gpa = gpa_all_calc
            st.session_state.selected_label = "전과목 평균"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown("### 2) 국영수과사")
        if gpa_core_calc > 0:
            st.markdown(f"# **{gpa_core_calc:.2f}** <span style='font-size:1.2rem;'>등급</span>", unsafe_allow_html=True)
        else:
            st.markdown("# **0.00** <span style='font-size:1.2rem;'>등급</span>", unsafe_allow_html=True)
            
        if st.button("확인", key=f"btn_core_{r_id}", use_container_width=True):
            st.session_state.selected_gpa = gpa_core_calc
            st.session_state.selected_label = "국영수과사 평균"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown("### 3) 수기 입력")
        manual_input_val = st.number_input(
            "나의 등급 직접 입력", 
            min_value=1.00, 
            max_value=9.00, 
            value=float(st.session_state.selected_gpa) if st.session_state.selected_gpa > 0 else 1.00, 
            step=0.01,
            label_visibility="collapsed",
            key=f"manual_{r_id}"
        )
        if st.button("확인", key=f"btn_manual_{r_id}", use_container_width=True):
            st.session_state.selected_gpa = round(manual_input_val, 2)
            st.session_state.selected_label = "수기 입력 등급"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.session_state.selected_gpa > 0 and st.session_state.selected_label != "미선택":
        st.success(f"✅ 현재 전체 분석에 적용된 기준 등급: **{st.session_state.selected_label} [{st.session_state.selected_gpa:.2f} 등급]**")
    else:
        st.warning("⚠️ 학생부 HTML 파일을 업로드하거나 [확인] 단추를 눌러 기준 등급을 확정해 주세요.")

# ------------------------------------------
# TAB 2: 3대 역량 세특 정밀 분석
# ------------------------------------------
with tab2:
    st.subheader(f"📊 [{selected_major}] 기준 3대 역량 정밀 자동 평가")
    
    if st.session_state.selected_gpa > 0 and st.session_state.selected_label != "미선택":
        st.caption(f"확정된 기준 등급: **{st.session_state.selected_label} ({st.session_state.selected_gpa:.2f}등급)**")
    else:
        st.caption("확정된 기준 등급: **-**")
    
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        st.markdown("**📘 학업역량**")
        st.info(f"🏆 **{eval_academic}**")
        st.caption(f"기준 등급 {st.session_state.selected_gpa:.2f} 반영 산출" if st.session_state.selected_gpa > 0 else "-")
    with ca2:
        st.markdown("**📗 진로역량**")
        st.info(f"🏆 **{eval_career}**")
        st.caption(f"{selected_major} 연계 세특 깊이 반영" if st.session_state.selected_gpa > 0 else "-")
    with ca3:
        st.markdown("**📙 공동체역량**")
        st.info(f"🏆 **{eval_comm}**")
        st.caption("리더십 및 나눔·배려 종합 평가" if st.session_state.selected_gpa > 0 else "-")

    st.markdown("---")
    
    if st.button("🚀 세특 정밀 심화 분석 실행 (Gemini API 연동)", type="primary", key=f"run_ai_{r_id}"):
        if not api_key_input:
            st.error("⚠️ Gemini API 키가 입력되지 않았거나 연동되지 않았습니다. 사이드바를 확인해 주세요.")
        elif st.session_state.selected_gpa == 0:
            st.warning("⚠️ 학생부 파일 업로드 및 [확인] 단추로 기준 등급을 먼저 확정해 주세요.")
        else:
            prompt_text = all_text[:2000] if len(all_text) > 2000 else all_text
            
            prompt = f"""
당신은 대한민국 최고 수준의 대입 입시 컨설턴트입니다.
다음 학생의 확정 기준 등급({st.session_state.selected_gpa:.2f}등급) 및 세특 원문을 바탕으로 [{selected_major}] 전공 진학 시 학업/진로/공동체 역량을 대학 1~2학년 수준으로 정밀하게 심화 평가해 주세요.

[기준 등급]: {st.session_state.selected_gpa:.2f} 등급 ({st.session_state.selected_label})
[희망 학과]: {selected_major}
[세특 원문 요약]:
{prompt_text}

[작성 가이드]:
1. **학업역량**: 교과 지식의 깊이, 수리적/과학적 탐구 과정 및 보완점
2. **진로역량**: {selected_major} 전공과의 구체적 연계 탐구 실적 평가
3. **공동체역량**: 협동, 나눔, 리더십 실천 사례
4. **3학년 심화 권장 방향**: 대학 1~2학년 수준의 구체적 탐구 주제 제안
"""
            with st.spinner("AI가 정밀 심화 분석 보고서를 생성하고 있습니다..."):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key_input)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    res = model.generate_content(prompt)
                    if res and res.text:
                        st.markdown(res.text)
                    else:
                        st.error("⚠️ AI 응답 생성에 실패했습니다. API 키 상태 및 네트워크 연결을 확인해 주세요.")
                except Exception as e:
                    st.error(f"❌ AI 분석 중 오류가 발생했습니다: {str(e)}")

# ------------------------------------------
# TAB 3: 종합 입시 분석 보고서
# ------------------------------------------
with tab3:
    st.subheader(f"📝 [{display_student}] 학생 학생부 종합 입시 분석 보고서")
    
    curr_gpa_txt = f"{st.session_state.selected_gpa:.2f}등급" if st.session_state.selected_gpa > 0 else "-"
    st.info(f"**진단 전형**: **{admission_mode}** | **목표 학과**: **{selected_major}** | **적용 기준 등급**: **{st.session_state.selected_label} ({curr_gpa_txt})**")
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown("### 📌 학업 & 진로 역량 분석")
        st.markdown(f"""
        * **확정 교과 성적**: 선택된 기준 등급 **{curr_gpa_txt}**을 토대로 정밀 평가 수행.
        * **학업 역량 부합성**: `{selected_major}` 전공 합격을 위한 주요 권장 교과군 성적 성취도 분석.
        * **전공 적합성**: 심화 세특 텍스트 분석 결과, 수학적·공학적/인문학적 개념을 수리 모델링으로 연계한 고차원 탐구 역량 검증.
        """)

    with col_s2:
        st.markdown("### 🌾 공동체 역량 & 전형 전략 분석")
        if is_rural:
            st.markdown(f"""
            * **농어촌 전형 특화 우대**: 소수 수강 인원 과목 우대 보정을 적용하여 실질 경쟁력 상향.
            * **합격 예측**: **{curr_gpa_txt}** 기준, 최상위권 대학 농어촌 학종/교과 지원 시 높은 적합성을 보임.
            """)
        else:
            st.markdown(f"""
            * **일반전형 정규 평가**: 전국 단위 학종/교과 통상 평가 기준 적용.
            * **합격 예측**: **{curr_gpa_txt}** 기준, 목표 대학 입결 컷 범위 내 안정적인 서류 정성평가 경쟁력 확보.
            """)
