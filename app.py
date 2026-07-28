import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup

# PDF 파싱 라이브러리
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# =====================================================================
# 1. 데이터 로드 및 열 이름 매핑
# =====================================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("2026 수시정리.csv", encoding="utf-8-sig")
        
        column_mapping = {
            "대학명": "대학",
            "학과명": "학과",
            "전형명": "전형",
            "2026등급컷I": "50%컷",
            "2026등급컷II": "70%컷",
            "2026등급컷III": "90%컷",
            "2025등급컷2": "50%컷_prev",
            "2025등급컷": "70%컷_prev"
        }
        df = df.rename(columns=column_mapping)
        
        # 필수 열 보완
        if "50%컷" not in df.columns and "50%컷_prev" in df.columns:
            df["50%컷"] = df["50%컷_prev"]
        if "70%컷" not in df.columns and "70%컷_prev" in df.columns:
            df["70%컷"] = df["70%컷_prev"]
        if "90%컷" not in df.columns:
            df["90%컷"] = df["70%컷"]
            
        if "필수과목" not in df.columns:
            df["필수과목"] = ""
            
        df = df.dropna(subset=["지역", "대학", "학과"])
        
    except FileNotFoundError:
        sample_data = {
            "지역": ["서울", "서울", "서울", "서울", "서울", "서울"],
            "대학": ["서울대학교", "서울대학교", "건국대학교", "성균관대학교", "연세대학교", "고려대학교"],
            "학과": ["간호대학", "의예과", "교육공학과", "교육학과", "컴퓨터과학과", "의과대학"],
            "전형": ["사회통합", "지역균형", "KU자기추천", "성균인재", "활동우수형", "학업우수형"],
            "50%컷": [1.45, 1.05, 1.85, 1.62, 1.35, 1.15],
            "70%컷": [1.60, 1.12, 1.98, 1.75, 1.48, 1.22],
            "90%컷": [1.75, 1.20, 2.10, 1.88, 1.60, 1.30],
            "필수과목": ["독서, 문학", "화학Ⅱ, 생명과학Ⅱ", "교육학, 심리학", "교육학, 사회문화", "미적분, 기하", "생명과학Ⅱ"]
        }
        df = pd.DataFrame(sample_data)
        
    return df

df = load_data()

# =====================================================================
# 2. 파일 텍스트 추출 (TXT, HTML, PDF)
# =====================================================================
def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    if file_type == 'txt':
        return uploaded_file.read().decode("utf-8", errors="ignore")
    
    elif file_type in ['html', 'htm']:
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text(separator=' ')
    
    elif file_type == 'pdf':
        if pdfplumber is not None:
            text = ""
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        else:
            st.error("PDF 파싱 라이브러리(pdfplumber)가 필요합니다.")
            return ""
    return ""

# =====================================================================
# 3. 내신 등급 계산 및 교과별 분석 Engine
# =====================================================================
KOREAN_SUBS = ["국어", "화법", "작문", "문학", "독서", "언어"]
MATH_SUBS = ["수학", "미적분", "기하", "확률", "통계", "수학Ⅰ", "수학Ⅱ"]
ENG_SUBS = ["영어", "회화", "독해", "작문"]
SCI_SUBS = ["물리학", "화학", "생명과학", "지구과학", "과학"]
SOC_SUBS = ["한국사", "역사", "지리", "일반사회", "윤리", "사상", "정치", "법", "경제", "사회"]

def categorize_subject(name):
    for k in KOREAN_SUBS:
        if k in name: return "국어"
    for m in MATH_SUBS:
        if m in name: return "수학"
    for e in ENG_SUBS:
        if e in name: return "영어"
    for s in SCI_SUBS:
        if s in name: return "과학"
    for sc in SOC_SUBS:
        if sc in name: return "사회"
    return "기타"

def parse_detailed_gpa(text):
    # 단위 및 등급 패턴 파싱
    pattern = re.compile(r'([가-힣A-Za-z0-9ⅠⅡIⅡ]+)\s*\(?(\d+)\s*단위\s*[\s/,\-_]*\s*(\d+)\s*등급\)?')
    matches = pattern.findall(text)
    
    subjects = []
    cat_data = {"전과목": [], "국영수과사": [], "국영수과": [], "국영수사": []}
    
    for match in matches:
        sub_name, unit, rank = match[0], int(match[1]), int(match[2])
        cat = categorize_subject(sub_name)
        item = {"과목": sub_name, "단위": unit, "등급": rank, "분류": cat}
        subjects.append(item)
        
        cat_data["전과목"].append(item)
        if cat in ["국어", "수학", "영어", "과학", "사회"]:
            cat_data["국영수과사"].append(item)
        if cat in ["국어", "수학", "영어", "과학"]:
            cat_data["국영수과"].append(item)
        if cat in ["국어", "수학", "영어", "사회"]:
            cat_data["국영수사"].append(item)
            
    def calc_gpa(sub_list):
        tot_rc = sum(x["등급"] * x["단위"] for x in sub_list)
        tot_c = sum(x["단위"] for x in sub_list)
        return round(tot_rc / tot_c, 2) if tot_c > 0 else 0.0

    gpa_results = {
        "전과목": calc_gpa(cat_data["전과목"]),
        "국영수과사": calc_gpa(cat_data["국영수과사"]),
        "국영수과": calc_gpa(cat_data["국영수과"]),
        "국영수사": calc_gpa(cat_data["국영수사"])
    }
    return gpa_results, subjects

# =====================================================================
# 4. 비교과 정량/정성 정밀 분석 알고리즘
# =====================================================================
def map_score_to_grade(pct):
    if pct >= 100: return "상상"
    elif pct >= 95: return "상중"
    elif pct >= 90: return "상하"
    elif pct >= 85: return "중상"
    elif pct >= 80: return "중중"
    elif pct >= 70: return "중하"
    else: return "하"

def analyze_non_subject(text, subjects_data):
    # 2-1-3 학업성취도 (A,B,C 비율)
    a_count = len(re.findall(r'\bA\b', text))
    b_count = len(re.findall(r'\bB\b', text))
    c_count = len(re.findall(r'\bC\b', text))
    tot_achievement = a_count + b_count + c_count
    
    a_pct = (a_count / tot_achievement * 100) if tot_achievement > 0 else 100
    academic_achievement_grade = map_score_to_grade(a_pct)
    
    # 2-1-3 학업태도 및 탐구력 키워드
    keywords_academic = [
        "적극적", "배우고자", "의지", "노력", "심화", "문제 해결", "지적호기심", 
        "궁금증", "자기주도", "탐구", "보고서", "발발표", "토론", "논리적", 
        "확장", "독후", "성장", "질문"
    ]
    matched_acad = sum(1 for kw in keywords_academic if kw in text)
    acad_pct = min(100, (matched_acad / 12) * 100)
    academic_attitude_grade = map_score_to_grade(acad_pct)
    
    # 2-2 진로역량 평가
    # 진로교과 성취도 B 개수 파악
    career_b_count = b_count
    if career_b_count == 0:
        career_subject_eval = "우수"
    elif career_b_count <= 2:
        career_subject_eval = "보통"
    else:
        career_subject_eval = "미흡"
        
    # 4대 세부 평가
    has_reading = len(re.findall(r'독서|독후|서적|도서', text)) >= 2
    has_presentation = len(re.findall(r'보고서|발표|토론', text)) >= 2
    
    def eval_sub_aspect(keyword_list):
        matches = sum(1 for k in keyword_list if k in text)
        if matches >= 3 and has_reading and has_presentation:
            return "우수"
        elif matches >= 1:
            return "보통"
        else:
            return "미흡"
            
    eval_course = eval_sub_aspect(["권장", "이수", "점수", "상승", "우수"])
    eval_setek = eval_sub_aspect(["탐구", "주제", "이해도", "확장성", "개념"])
    eval_club = eval_sub_aspect(["동아리", "주도적", "역할", "해결", "협력"])
    
    # 2-3 공동체역량 평가
    executive_count = len(re.findall(r'회장|반장|부회장|부반장|부장|임원', text))
    community_kw = ["소외", "역할", "분담", "멘토링", "갈등", "해결", "소통", "나눔", "배려", "성실", "규칙", "리더십"]
    comm_matches = sum(1 for k in community_kw if k in text)
    
    def eval_community():
        if executive_count >= 3 or comm_matches >= 4:
            return "우수", "우수", "우수"
        elif executive_count in [1, 2] or comm_matches >= 2:
            return "보통", "우수", "보통"
        else:
            return "미흡", "보통", "미흡"
            
    comm_hangeuk, comm_changche, comm_setek = eval_community()
    
    return {
        "학업성취도_등급": academic_achievement_grade,
        "학업태도_등급": academic_attitude_grade,
        "진로교과이수": career_subject_eval,
        "진로_교과학습": eval_course,
        "진로_교과세특": eval_setek,
        "진로_동아리": eval_club,
        "공동체_행특": comm_hangeuk,
        "공동체_창체": comm_changche,
        "공동체_교과세특": comm_setek
    }

# =====================================================================
# 5. UI 및 레이아웃 설정
# =====================================================================
st.set_page_config(page_title="천명의선택 학생부 NAVI", layout="centered")

st.markdown("""
    <style>
    .title-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    .main-title-text {
        font-size: 30px;
        font-weight: 900;
        color: #F8FAFC !important;
        margin-bottom: 6px;
    }
    .sub-title-text {
        font-size: 14px;
        color: #93C5FD !important;
        font-weight: 500;
    }
    .step-header {
        background-color: #1E293B;
        color: #F8FAFC !important;
        font-weight: bold;
        font-size: 15px;
        padding: 10px 16px;
        border-radius: 8px;
        border-left: 6px solid #3B82F6;
        margin-top: 20px;
        margin-bottom: 15px;
    }
    </style>
    
    <div class="title-card">
        <div class="main-title-text">🎓 천명의선택 학생부 NAVI</div>
        <div class="sub-title-text">입시 컨설턴트 전용 - 학생부 정밀 종합 진단 및 3개 대학 비교 분석 프로</div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# [STEP 1] 희망 지역 및 3개 대학/학과 선택
# ---------------------------------------------------------------------
st.markdown('<div class="step-header">[STEP 1] 대학 및 학과 선택 (상담 대학 3곳 고정)</div>', unsafe_allow_html=True)

region_list = sorted(df["지역"].astype(str).unique())
selected_region = st.selectbox("📍 지원 목표 지역 선택 (공통)", region_list, index=0)
region_df = df[df["지역"] == selected_region]

selected_targets = []

for i in range(1, 4):
    st.markdown(f"**📌 {i}지망 선택**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        univ_list = sorted(region_df["대학"].astype(str).unique())
        univ = st.selectbox(f"대학 {i}", univ_list, key=f"univ_{i}")
        
    with col2:
        dept_list = sorted(region_df[region_df["대학"] == univ]["학과"].astype(str).unique())
        dept = st.selectbox(f"학과 {i}", dept_list, key=f"dept_{i}")
        
    with col3:
        sub_df = region_df[(region_df["대학"] == univ) & (region_df["학과"] == dept)]
        type_list = sorted(sub_df["전형"].astype(str).unique())
        sel_type = st.selectbox(f"전형 {i}", type_list, key=f"type_{i}")
        
    target_row = sub_df[sub_df["전형"] == sel_type].iloc[0]
    selected_targets.append({
        "label": f"{i}지망",
        "region": selected_region,
        "univ": univ,
        "dept": dept,
        "type": sel_type,
        "row": target_row
    })
    if i < 3:
        st.divider()

# ---------------------------------------------------------------------
# [STEP 2] 학생부 파일 업로드
# ---------------------------------------------------------------------
st.markdown('<div class="step-header">[STEP 2] 학생부 파일 업로드 (HTML 또는 PDF)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "학생부 파일(.html, .pdf, .txt)을 업로드해 주세요.", 
    type=["html", "htm", "pdf", "txt"]
)

sample_record_text = """[교과학습발달상황]
국어 (4단위/2등급) A
수학 (4단위/1등급) A
영어 (4단위/2등급) A
화학Ⅰ (3단위/1등급) A
생명과학Ⅰ (3단위/2등급) B
화학Ⅱ (3단위/2등급) A
생명과학Ⅱ (3단위/1등급) A
[세부능력 및 특기사항]
국어: 수업 시간에 적극적으로 참여하며 배우고자 하는 의지가 강함. 독후 활동으로 관련 주제 탐구 보고서 작성함.
수학: 지적호기심이 풍부하여 심화 문제 해결 과정에서 논리적 사고력을 보여줌. 발표 및 토론에 자기주도적으로 참여함.
동아리: 동아리 부장으로서 부원들의 의견을 수용하고 역할을 분담하여 갈등을 성공적으로 해결함. 소통과 리더십 발휘.
행동특성: 학급 회장으로서 성실하고 나눔과 배려를 실천함. 멘토링 활동을 통해 친구들의 학업 성장을 도움.
"""

use_sample = st.checkbox("파일이 없는 경우 테스트용 샘플 데이터 적용하기")

# ---------------------------------------------------------------------
# [STEP 3] 학생부 종합 정밀 분석 및 리포트 도출
# ---------------------------------------------------------------------
st.markdown('<div class="step-header">[STEP 3] 분석 결과 확인</div>', unsafe_allow_html=True)

start_button = st.button("🎓 학생부 정밀 분석 시작", type="primary", use_container_width=True)

if start_button:
    record_text = ""
    if uploaded_file is not None:
        record_text = extract_text_from_file(uploaded_file)
    elif use_sample:
        record_text = sample_record_text
        st.info("샘플 텍스트 데이터가 적용되었습니다.")
    else:
        st.warning("⚠️ 학생부 파일을 업로드하거나 '샘플 데이터 적용하기'를 선택해 주세요.")

    if record_text:
        # 내신 및 정성 분석 실행
        gpa_res, subjects = parse_detailed_gpa(record_text)
        non_sub_res = analyze_non_subject(record_text, subjects)
        
        # 대학별 컷 데이터 정리
        cut_cards_html = ""
        for item in selected_targets:
            r = item["row"]
            c50 = f"{float(r['50%컷']):.2f}" if pd.notna(r.get('50%컷')) else "미공개"
            c70 = f"{float(r['70%컷']):.2f}" if pd.notna(r.get('70%컷')) else "미공개"
            c90 = f"{float(r['90%컷']):.2f}" if pd.notna(r.get('90%컷')) else "미공개"
            
            cut_cards_html += f"""
            <div style="flex: 1; min-width: 200px; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; background-color: #F8FAFC; margin: 4px;">
                <div style="font-weight: bold; color: #1E3A8A; font-size: 13px;">[{item['label']}] {item['univ']}</div>
                <div style="font-size: 14px; font-weight: bold; color: #0F172A; margin-bottom: 8px;">{item['dept']} ({item['type']})</div>
                <div style="font-size: 12px; color: #334155;">
                    • 50% 컷: <b>{c50}</b><br>
                    • 70% 컷: <b>{c70}</b><br>
                    • 90% 컷: <b>{c90}</b>
                </div>
            </div>
            """

        report_html = f"""
        <div id="print-area" style="padding: 25px; border: 2px solid #1E3A8A; border-radius: 12px; font-family: 'Malgun Gothic', sans-serif; background-color: #FFFFFF; color: #333333; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="font-size: 12px; color: #1E3A8A; font-weight: bold; border: 1px solid #1E3A8A; padding: 3px 8px; border-radius: 20px;">천명의선택 NAVI</span>
                <h2 style="color: #1E3A8A; margin-top: 8px; margin-bottom: 5px; font-size: 24px;">수시 학생부 종합분석 보고서</h2>
            </div>
            
            <!-- 1. 학생부 내신 등급 분석 -->
            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">1. 학생부 교과 내신 등급 산출 결과</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; text-align: center; font-size: 14px;">
                <tr style="background-color: #1E3A8A; color: white; font-weight: bold;">
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">전과목 평균</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">국영수과사</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">국영수과</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">국영수사</td>
                </tr>
                <tr style="font-size: 16px; font-weight: bold; color: #DC2626;">
                    <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_res['전과목']} 등급</td>
                    <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_res['국영수과사']} 등급</td>
                    <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_res['국영수과']} 등급</td>
                    <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_res['국영수사']} 등급</td>
                </tr>
            </table>

            <!-- 2. 목표 대학 입결 컷 비교 -->
            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">2. 상담 선택 대학 입결 컷 지표 (50% / 70% / 90%)</h3>
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; margin-bottom: 20px;">
                {cut_cards_html}
            </div>

            <!-- 3. 비교과 역량 정밀 평가 -->
            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">3. 학생부 비교과 정량/정성 역량 진단</h3>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px;">
                <tr style="background-color: #F1F5F9; font-weight: bold; color: #1E3A8A;">
                    <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: center;" width="25%">평가 역량</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: center;" width="50%">세부 평가 항목</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: center;" width="25%">진단 등급</th>
                </tr>
                <!-- 학업역량 -->
                <tr>
                    <td rowspan="2" style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; background-color: #FAF5FF;">학업역량</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">학업성취도 (A, B, C 성취도 비율)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #2563EB;">{non_sub_res['학업성취도_등급']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">학업태도 및 탐구력 (세특 키워드 반영)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #2563EB;">{non_sub_res['학업태도_등급']}</td>
                </tr>
                <!-- 진로역량 -->
                <tr>
                    <td rowspan="4" style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; background-color: #EFF6FF;">진로역량</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">진로선택 교과 이수 성취도 (A/B/C)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #059669;">{non_sub_res['진로교과이수']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">진로역량 - 교과학습 (권장과목/성적추이)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #059669;">{non_sub_res['진로_교과학습']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">진로역량 - 교과세특 (주제탐구/발표)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #059669;">{non_sub_res['진로_교과세특']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">진로역량 - 동아리 활동 (주도성/해결)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #059669;">{non_sub_res['진로_동아리']}</td>
                </tr>
                <!-- 공동체역량 -->
                <tr>
                    <td rowspan="3" style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; background-color: #F0FDF4;">공동체역량</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">공동체역량 - 행동특성 및 종합의견</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #D97706;">{non_sub_res['공동체_행특']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">공동체역량 - 창체 (동아리, 자율, 봉사)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #D97706;">{non_sub_res['공동체_창체']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">공동체역량 - 교과세특 (소통/협업)</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #D97706;">{non_sub_res['공동체_교과세특']}</td>
                </tr>
            </table>
        </div>
        
        <div style="text-align: center; margin-top: 15px;">
            <button onclick="window.print()" style="padding: 10px 24px; background-color: #1E3A8A; color: white; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer;">
                🖨️ 분석 보고서 PDF 저장 / 인쇄
            </button>
        </div>
        """
        
        st.markdown("### 📊 정밀 종합 분석 보고서")
        st.components.v1.html(report_html, height=700, scrolling=True)
