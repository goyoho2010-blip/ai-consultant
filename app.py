import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# =====================================================================
# 1. 대학 입결 데이터 로드 및 열 매핑
# =====================================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("2026 수시정리.csv", encoding="utf-8-sig")
        column_mapping = {
            "대학명": "대학", "학과명": "학과", "전형명": "전형",
            "2026등급컷I": "50%컷", "2026등급컷II": "70%컷", "2026등급컷III": "90%컷",
            "2025등급컷2": "50%컷_prev", "2025등급컷": "70%컷_prev"
        }
        df = df.rename(columns=column_mapping)
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
            "지역": ["서울", "서울", "서울"],
            "대학": ["서울대학교", "고려대학교", "연세대학교"],
            "학과": ["의예과", "의과대학", "컴퓨터과학과"],
            "전형": ["지역균형", "학업우수형", "활동우수형"],
            "50%컷": [1.05, 1.15, 1.35],
            "70%컷": [1.12, 1.22, 1.48],
            "90%컷": [1.20, 1.30, 1.60],
            "필수과목": ["화학Ⅱ, 생명과학Ⅱ", "생명과학Ⅱ", "미적분, 기하"]
        }
        df = pd.DataFrame(sample_data)
    return df

df_univ = load_data()

# =====================================================================
# 2. 교과군 분류 및 파일 파서
# =====================================================================
KOREAN = ["국어", "화법", "작문", "문학", "독서", "언어"]
MATH = ["수학", "미적분", "기하", "확률", "통계", "수학Ⅰ", "수학Ⅱ"]
ENG = ["영어", "회화", "독해", "작문"]
SCI = ["물리학", "화학", "생명과학", "지구과학", "과학"]
SOC = ["한국사", "역사", "지리", "일반사회", "윤리", "사상", "정치", "법", "경제", "사회"]

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

def parse_html_neis(content):
    soup = BeautifulSoup(content, 'html.parser')
    parsed_rows = []
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
            if len(cols) >= 5:
                sub_candidate = cols[1] if len(cols) > 1 else ""
                for idx, text in enumerate(cols):
                    unit_match = re.search(r'^\d+$', text)
                    rank_match = re.search(r'^([1-9])\b', text)
                    if unit_match and rank_match and idx > 1:
                        unit = int(unit_match.group())
                        rank = int(rank_match.group(1))
                        cat = classify_category(sub_candidate)
                        parsed_rows.append({
                            "학년": 1, "과목명": sub_candidate,
                            "교과군": cat, "단위수": unit, "석차등급": rank
                        })
                        break
    return parsed_rows, soup.get_text(separator=' ')

def parse_text_record(text):
    pattern = re.compile(r'([가-힣0-9IⅠⅡIII]+)\s*\(?(\d+)\s*단위\s*[\s/,\-_]*\s*(\d+)\s*등급\)?')
    matches = pattern.findall(text)
    parsed_rows = []
    for match in matches:
        sub_name, unit, rank = match[0], int(match[1]), int(match[2])
        cat = classify_category(sub_name)
        parsed_rows.append({
            "학년": 1, "과목명": sub_name,
            "교과군": cat, "단위수": unit, "석차등급": rank
        })
    return parsed_rows

def calculate_gpa_by_groups(df_subjects, target_groups=None):
    if df_subjects.empty:
        return 0.0
    filtered = df_subjects.copy()
    if target_groups:
        filtered = filtered[filtered["교과군"].isin(target_groups)]
    
    valid = filtered[pd.to_numeric(filtered["석차등급"], errors="coerce").notnull()].copy()
    if valid.empty:
        return 0.0
        
    valid["석차등급"] = valid["석차등급"].astype(float)
    valid["단위수"] = valid["단위수"].astype(float)
    
    tot_credits = valid["단위수"].sum()
    if tot_credits == 0:
        return 0.0
    weighted_sum = (valid["석차등급"] * valid["단위수"]).sum()
    return round(weighted_sum / tot_credits, 2)

# =====================================================================
# 3. 비교과 3대 역량 정밀 정량/정성 평가 엔진
# =====================================================================
def map_score_to_grade(pct):
    if pct >= 100: return "상상"
    elif pct >= 95: return "상중"
    elif pct >= 90: return "상하"
    elif pct >= 85: return "중상"
    elif pct >= 80: return "중중"
    elif pct >= 70: return "중하"
    else: return "하"

def analyze_non_subject(full_text):
    if not full_text:
        full_text = ""
        
    # 2-1 학업역량: 학업성취도 (A,B,C 비율)
    a_count = len(re.findall(r'\bA\b', full_text))
    b_count = len(re.findall(r'\bB\b', full_text))
    c_count = len(re.findall(r'\bC\b', full_text))
    tot_abc = a_count + b_count + c_count
    a_pct = (a_count / tot_abc * 100) if tot_abc > 0 else 100.0
    grade_achievement = map_score_to_grade(a_pct)
    
    # 학업태도 및 탐구력 키워드 평가
    acad_keywords = ["적극적", "배우고자", "의지", "노력", "심화", "문제 해결", "지적호기심", 
                     "궁금증", "자기주도", "탐구", "보고서", "발표", "토론", "논리적", "확장", "독후", "성장", "질문"]
    matched_acad = sum(1 for kw in acad_keywords if kw in full_text)
    acad_pct = min(100.0, (matched_acad / 10.0) * 100.0)
    grade_attitude = map_score_to_grade(acad_pct)
    
    # 2-2 진로역량 평가
    career_b_eval = "우수" if b_count == 0 else ("보통" if b_count <= 2 else "미흡")
    has_reading = len(re.findall(r'독서|독후|서적|도서', full_text)) >= 2
    has_presentation = len(re.findall(r'보고서|발표|토론', full_text)) >= 2
    
    def eval_aspect(keywords):
        m = sum(1 for k in keywords if k in full_text)
        if m >= 2 and has_reading and has_presentation:
            return "우수"
        elif m >= 1:
            return "보통"
        else:
            return "미흡"
            
    eval_course = eval_aspect(["권장", "이수", "점수", "상승", "우수"])
    eval_setek = eval_aspect(["탐구", "주제", "이해도", "확장성", "개념"])
    eval_club = eval_aspect(["동아리", "주도적", "역할", "해결", "협력"])
    
    # 2-3 공동체역량 평가 (임원 활동 가산점 반영)
    exec_count = len(re.findall(r'회장|반장|부회장|부반장|부장|임원', full_text))
    comm_keywords = ["소외", "역할", "분담", "멘토링", "갈등", "해결", "소통", "나눔", "배려", "성실", "규칙", "리더십"]
    comm_m = sum(1 for k in comm_keywords if k in full_text)
    
    if exec_count >= 3 or comm_m >= 4:
        c_hangeuk, c_changche, c_setek = "우수", "우수", "우수"
    elif exec_count in [1, 2] or comm_m >= 2:
        c_hangeuk, c_changche, c_setek = "보통", "우수", "보통"
    else:
        c_hangeuk, c_changche, c_setek = "미흡", "보통", "미흡"
        
    return {
        "학업성취도": grade_achievement,
        "학업태도": grade_attitude,
        "진로교과이수": career_b_eval,
        "진로_교과학습": eval_course,
        "진로_교과세특": eval_setek,
        "진로_동아리": eval_club,
        "공동체_행특": c_hangeuk,
        "공동체_창체": c_changche,
        "공동체_교과세특": c_setek
    }

# =====================================================================
# 4. Streamlit UI 및 세션 관리
# =====================================================================
st.set_page_config(page_title="천명의선택 학생부 NAVI", layout="wide")

st.markdown("""
    <style>
    .title-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        border: 2px solid #3B82F6; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;
    }
    .main-title-text { font-size: 28px; font-weight: 900; color: #F8FAFC !important; }
    .sub-title-text { font-size: 14px; color: #93C5FD !important; }
    .step-header {
        background-color: #1E293B; color: #F8FAFC !important; font-weight: bold; font-size: 15px;
        padding: 10px 16px; border-radius: 8px; border-left: 6px solid #3B82F6; margin-top: 15px; margin-bottom: 15px;
    }
    </style>
    <div class="title-card">
        <div class="main-title-text">🎓 천명의선택 학생부 NAVI</div>
        <div class="sub-title-text">입시 컨설턴트 전용 - 학생부 정밀 종합 진단 및 3개 대학 비교 분석 프로</div>
    </div>
""", unsafe_allow_html=True)

if 'subject_data' not in st.session_state:
    st.session_state['subject_data'] = pd.DataFrame([
        {"학년": 1, "과목명": "국어 (4단위/2등급) A", "교과군": "국어", "단위수": 4, "석차등급": 2},
        {"학년": 1, "과목명": "수학Ⅰ (4단위/1등급) A", "교과군": "수학", "단위수": 4, "석차등급": 1},
        {"학년": 1, "과목명": "영어Ⅰ (4단위/2등급) A", "교과군": "영어", "단위수": 4, "석차등급": 2},
        {"학년": 2, "과목명": "화학Ⅰ (3단위/1등급) A", "교과군": "과학", "단위수": 3, "석차등급": 1},
        {"학년": 2, "과목명": "생명과학Ⅰ (3단위/2등급) B", "교과군": "과학", "단위수": 3, "석차등급": 2},
    ])

if 'full_text' not in st.session_state:
    st.session_state['full_text'] = """
    수업 시간에 적극적으로 참여하며 배우고자 하는 의지가 강함. 독후 활동으로 관련 주제 탐구 보고서 작성함.
    지적호기심이 풍부하여 심화 문제 해결 과정에서 논리적 사고력을 보여줌. 발표 및 토론에 자기주도적으로 참여함.
    동아리 부장으로서 부원들의 의견을 수용하고 역할을 분담하여 갈등을 성공적으로 해결함. 소통과 리더십 발휘.
    학급 회장으로서 성실하고 나눔과 배려를 실천함. 멘토링 활동을 통해 친구들의 학업 성장을 도움.
    """

# ---------------------------------------------------------------------
# [STEP 1] 목표 대학 3곳 지정
# ---------------------------------------------------------------------
st.markdown('<div class="step-header">[STEP 1] 대학 및 학과 선택 (상담 대학 3곳 고정)</div>', unsafe_allow_html=True)

region_list = sorted(df_univ["지역"].astype(str).unique())
selected_region = st.selectbox("📍 지원 목표 지역 선택 (공통)", region_list, index=0)
region_df = df_univ[df_univ["지역"] == selected_region]

selected_targets = []
cols_target = st.columns(3)
for i in range(1, 4):
    with cols_target[i-1]:
        st.markdown(f"**📌 {i}지망**")
        univ_list = sorted(region_df["대학"].astype(str).unique())
        univ = st.selectbox(f"대학 {i}", univ_list, key=f"u_{i}")
        dept_list = sorted(region_df[region_df["대학"] == univ]["학과"].astype(str).unique())
        dept = st.selectbox(f"학과 {i}", dept_list, key=f"d_{i}")
        sub_df = region_df[(region_df["대학"] == univ) & (region_df["학과"] == dept)]
        type_list = sorted(sub_df["전형"].astype(str).unique())
        sel_type = st.selectbox(f"전형 {i}", type_list, key=f"t_{i}")
        target_row = sub_df[sub_df["전형"] == sel_type].iloc[0]
        selected_targets.append({"label": f"{i}지망", "univ": univ, "dept": dept, "type": sel_type, "row": target_row})

# ---------------------------------------------------------------------
# [STEP 2] 학생부 파일 업로드 및 성적 보정
# ---------------------------------------------------------------------
st.markdown('<div class="step-header">[STEP 2] 학생부 파일 업로드 (HTML 또는 PDF) 및 성적 수정</div>', unsafe_allow_html=True)

col_up, col_edit = st.columns([2, 1])

with col_up:
    uploaded_file = st.file_uploader("학생부 파일(.html, .pdf, .txt)을 업로드하세요", type=["html", "htm", "pdf", "txt"])
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        parsed_list = []
        raw_text = ""
        if file_ext in ['html', 'htm']:
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            parsed_list, raw_text = parse_html_neis(content)
            if not parsed_list:
                parsed_list = parse_text_record(raw_text)
        elif file_ext == 'pdf' and pdfplumber:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    raw_text += (page.extract_text() or "") + "\n"
            parsed_list = parse_text_record(raw_text)
        elif file_ext == 'txt':
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
            parsed_list = parse_text_record(raw_text)
            
        if parsed_list:
            st.session_state['subject_data'] = pd.DataFrame(parsed_list)
            st.session_state['full_text'] = raw_text
            st.success(f"✅ 파일에서 총 {len(parsed_list)}개 과목 성적 및 세특 텍스트를 추출했습니다!")

with col_edit:
    edit_popover = st.popover("✏️ 내신 등급 직접 수정 / 추가 (상담용)", use_container_width=True)

with edit_popover:
    st.markdown("### 📝 성적 보정 및 미기재 과목 추가")
    st.caption("시험 전 예상 등급이나 학생부 미기재 성적을 직접 수정/추가하여 리포트에 즉시 반영합니다.")
    edited_df = st.data_editor(
        st.session_state['subject_data'],
        num_rows="dynamic",
        column_config={
            "학년": st.column_config.NumberColumn("학년", min_value=1, max_value=3, step=1, required=True),
            "과목명": st.column_config.TextColumn("과목명", required=True),
            "교과군": st.column_config.SelectboxColumn("교과군", options=["국어", "수학", "영어", "과학", "사회", "기타"], required=True),
            "단위수": st.column_config.NumberColumn("단위수", min_value=1, max_value=10, step=1, required=True),
            "석차등급": st.column_config.NumberColumn("석차등급(1~9)", min_value=1.0, max_value=9.0, step=0.1, required=True),
        },
        use_container_width=True,
        key="main_editor"
    )
    if st.button("수정 및 추가사항 적용", type="primary"):
        st.session_state['subject_data'] = edited_df
        st.success("보정된 성적 데이터가 즉시 반영되었습니다.")
        st.rerun()

# ---------------------------------------------------------------------
# [STEP 3] 정밀 종합 분석 보고서 출력
# ---------------------------------------------------------------------
st.markdown('<div class="step-header">[STEP 3] 분석 결과 확인</div>', unsafe_allow_html=True)

df_curr = st.session_state['subject_data']
full_txt_curr = st.session_state['full_text']

# 내신 계산
gpa_all = calculate_gpa_by_groups(df_curr)
gpa_kremss = calculate_gpa_by_groups(df_curr, ['국어', '영어', '수학', '과학', '사회'])
gpa_krems = calculate_gpa_by_groups(df_curr, ['국어', '영어', '수학', '과학'])
gpa_krms = calculate_gpa_by_groups(df_curr, ['국어', '영어', '수학', '사회'])

# 비교과 역량 분석
non_sub_res = analyze_non_subject(full_txt_curr)

# 대학별 컷 지표 카드 생성
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
    
    <!-- 1. 내신 산출 결과 -->
    <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">1. 학생부 교과 내신 등급 산출 결과</h3>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; text-align: center; font-size: 14px;">
        <tr style="background-color: #1E3A8A; color: white; font-weight: bold;">
            <td style="padding: 8px; border: 1px solid #CBD5E1;">전과목 평균</td>
            <td style="padding: 8px; border: 1px solid #CBD5E1;">국영수과사</td>
            <td style="padding: 8px; border: 1px solid #CBD5E1;">국영수과</td>
            <td style="padding: 8px; border: 1px solid #CBD5E1;">국영수사</td>
        </tr>
        <tr style="font-size: 18px; font-weight: bold; color: #DC2626;">
            <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_all} 등급</td>
            <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_kremss} 등급</td>
            <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_krems} 등급</td>
            <td style="padding: 10px; border: 1px solid #CBD5E1;">{gpa_krms} 등급</td>
        </tr>
    </table>

    <!-- 2. 목표 대학 컷 지표 -->
    <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">2. 상담 선택 대학 입결 컷 지표 (50% / 70% / 90%)</h3>
    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; margin-bottom: 20px;">
        {cut_cards_html}
    </div>

    <!-- 3. 비교과 3대 역량 진단 -->
    <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">3. 학생부 비교과 정량/정성 역량 진단</h3>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px;">
        <tr style="background-color: #F1F5F9; font-weight: bold; color: #1E3A8A;">
            <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: center;" width="25%">평가 역량</th>
            <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: center;" width="50%">세부 평가 항목</th>
            <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: center;" width="25%">진단 등급</th>
        </tr>
        <tr>
            <td rowspan="2" style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; background-color: #FAF5FF;">학업역량</td>
            <td style="padding: 8px; border: 1px solid #CBD5E1;">학업성취도 (A, B, C 성취도 비율)</td>
            <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #2563EB;">{non_sub_res['학업성취도']}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #CBD5E1;">학업태도 및 탐구력 (세특 키워드 반영)</td>
            <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: center; font-weight: bold; color: #2563EB;">{non_sub_res['학업태도']}</td>
        </tr>
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

st.components.v1.html(report_html, height=720, scrolling=True)
