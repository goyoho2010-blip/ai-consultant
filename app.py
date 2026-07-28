import streamlit as st
import pandas as pd
import re
import html
from bs4 import BeautifulSoup

# PDF 파싱을 위한 기어
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# =====================================================================
# 1. 데이터 로드 및 열 이름 유연한 처리
# =====================================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("2026 수시정리.csv", encoding="utf-8-sig")
        
        column_mapping = {
            "대학명": "대학",
            "학과명": "학과",
            "전형명": "전형",
            "2025등급컷2": "50%컷",
            "2025등급컷": "70%컷"
        }
        df = df.rename(columns=column_mapping)
        
        if "필수과목" not in df.columns:
            df["필수과목"] = ""
            
        df = df.dropna(subset=["지역", "대학", "학과"])
        
    except FileNotFoundError:
        sample_data = {
            "지역": ["서울", "서울", "서울", "서울", "경기/인천", "경기/인천"],
            "대학": ["서울대학교", "서울대학교", "고려대학교", "연세대학교", "가천대학교", "가천대학교"],
            "학과": ["의예과", "컴퓨터공학과", "의과대학", "컴퓨터과학과", "의예과", "간호학과"],
            "전형": ["일반전형(학종)", "지역균형(학종)", "학업우수형(학종)", "활동우수형(학종)", "가천의예(학종)", "가천바람개비(학종)"],
            "50%컷": [1.05, 1.21, 1.15, 1.35, 1.10, 1.80],
            "70%컷": [1.12, 1.30, 1.22, 1.48, 1.18, 1.95],
            "필수과목": ["화학Ⅱ, 생명과학Ⅱ", "미적분, 기하", "생명과학Ⅱ", "미적분, 기하", "생명과학Ⅱ", "독서, 문학"]
        }
        df = pd.DataFrame(sample_data)
        
    return df

df = load_data()

# =====================================================================
# 2. 파일 파싱 (TXT, HTML, PDF) 및 내신 계산 함수
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
            st.error("PDF 파싱 라이브러리(pdfplumber)가 요구됩니다. txt/html 파일 또는 샘플로 테스트해보세요.")
            return ""
    return ""

def parse_student_record(text):
    pattern = re.compile(r'([가-힣]+)\s*\(?(\d+)\s*단위\s*[\s/,\-_]*\s*(\d+)\s*등급\)?')
    matches = pattern.findall(text)
    
    subjects = []
    total_rc = 0
    total_c = 0
    
    for match in matches:
        sub_name, unit, rank = match[0], int(match[1]), int(match[2])
        subjects.append({"과목": sub_name, "단위": unit, "등급": rank})
        total_rc += rank * unit
        total_c += unit
        
    gpa = round(total_rc / total_c, 2) if total_c > 0 else 0.0
    return gpa, subjects

# =====================================================================
# 3. Streamlit UI 구성 및 가독성 높은 폰트 색상 적용
# =====================================================================
st.set_page_config(page_title="천명의선택 학생부 NAVI", layout="centered")

st.markdown("""
    <style>
    .main-title {font-size: 30px; font-weight: bold; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .sub-title {font-size: 15px; color: #374151; text-align: center; margin-bottom: 25px;}
    /* 흰색 배경 박스에 진한 글씨색 고정으로 다크모드 글자 안보임 현상 해결 */
    .step-box {
        background-color: #E2E8F0; 
        color: #1E3A8A !important;
        font-weight: bold;
        font-size: 16px;
        padding: 12px 18px; 
        border-radius: 8px; 
        border-left: 6px solid #1E3A8A; 
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .choice-card {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .choice-card h4 {
        color: #1E3A8A;
        margin-top: 0;
        margin-bottom: 10px;
    }
    </style>
    <div class="main-title">🎓 천명의선택 학생부 NAVI</div>
    <div class="sub-title">2026학년도 학생부종합전형 정밀 진단 및 합격 예측 시뮬레이터</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# [STEP 1] 목표 대학 3곳 선택 (복수지망 기능)
# ---------------------------------------------------------------------
st.markdown('<div class="step-box">[STEP 1] 목표 대학 및 학과 선택 (최대 3곳 지정)</div>', unsafe_allow_html=True)

selected_targets = []

for i in range(1, 4):
    st.markdown(f"**📍 지망 {i} 선택**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        region_list = sorted(df["지역"].astype(str).unique())
        region = st.selectbox(f"지역 {i}", region_list, key=f"region_{i}")
        
    with col2:
        univ_list = sorted(df[df["지역"] == region]["대학"].astype(str).unique())
        univ = st.selectbox(f"대학 {i}", univ_list, key=f"univ_{i}")
        
    with col3:
        dept_list = sorted(df[(df["지역"] == region) & (df["대학"] == univ)]["학과"].astype(str).unique())
        dept = st.selectbox(f"학과 {i}", dept_list, key=f"dept_{i}")
        
    with col4:
        sub_df = df[(df["지역"] == region) & (df["대학"] == univ) & (df["학과"] == dept)]
        type_list = sorted(sub_df["전형"].astype(str).unique())
        sel_type = st.selectbox(f"전형 {i}", type_list, key=f"type_{i}")
        
    target_row = sub_df[sub_df["전형"] == sel_type].iloc[0]
    selected_targets.append({
        "label": f"지망 {i}",
        "region": region,
        "univ": univ,
        "dept": dept,
        "type": sel_type,
        "row": target_row
    })
    st.divider()

# ---------------------------------------------------------------------
# [STEP 2] 학생부 파일 업로드 (TXT, HTML, PDF 지원)
# ---------------------------------------------------------------------
st.markdown('<div class="step-box">[STEP 2] 학생부 파일을 업로드하세요</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "학생부 파일(.txt, .html, .pdf)을 업로드해 주세요.", 
    type=["txt", "html", "htm", "pdf"]
)

sample_record_text = """[교과학습발달상황]
국어 (4단위/2등급)
수학 (4단위/1등급)
영어 (4단위/2등급)
화학Ⅰ (3단위/1등급)
생명과학Ⅰ (3단위/2등급)
화학Ⅱ (3단위/2등급)
생명과학Ⅱ (3단위/1등급)
"""

use_sample = st.checkbox("파일이 없는 경우 샘플 데이터로 테스트하기")

record_text = ""
if uploaded_file is not None:
    record_text = extract_text_from_file(uploaded_file)
elif use_sample:
    record_text = sample_record_text
    st.info("샘플 텍스트가 적용되었습니다. 아래 버튼을 눌러 정밀 분석을 실행하세요.")

# ---------------------------------------------------------------------
# [STEP 3] 분석 결과 및 3개 대학 비교 보고서 생성
# ---------------------------------------------------------------------
if record_text:
    if st.button("학생부 정밀 분석 시작", type="primary", use_container_width=True):
        my_gpa, parsed_sub = parse_student_record(record_text)
        
        cards_html = ""
        for item in selected_targets:
            t_row = item["row"]
            
            try:
                cut_50 = float(t_row["50%컷"])
            except (ValueError, TypeError):
                cut_50 = 9.0
                
            try:
                cut_70 = float(t_row["70%컷"])
            except (ValueError, TypeError):
                cut_70 = 9.0
            
            if my_gpa <= cut_50 and cut_50 != 9.0:
                status = "안정 (합격 유력)"
                color = "#10B981"
            elif my_gpa <= cut_70 and cut_70 != 9.0:
                status = "적정 (경쟁력 있음)"
                color = "#3B82F6"
            else:
                status = "소신 (내신 보완 필요)"
                color = "#EF4444"
                
            c_50_str = f"{cut_50:.2f}" if cut_50 != 9.0 else "정보없음"
            c_70_str = f"{cut_70:.2f}" if cut_70 != 9.0 else "정보없음"
            
            cards_html += f"""
            <div style="flex: 1; min-width: 220px; border: 1px solid #D1D5DB; border-radius: 8px; padding: 15px; background-color: #F9FAFB; margin: 5px;">
                <div style="font-weight: bold; color: #1E3A8A; font-size: 14px; margin-bottom: 5px;">{item['label']}</div>
                <div style="font-size: 16px; font-weight: bold; color: #111827;">{item['univ']}</div>
                <div style="font-size: 14px; color: #4B5563; margin-bottom: 10px;">{item['dept']} ({item['type']})</div>
                <hr style="border: 0; border-top: 1px solid #E5E7EB; margin: 8px 0;">
                <div style="font-size: 12px; color: #6B7280;">50%컷: <b>{c_50_str}</b> | 70%컷: <b>{c_70_str}</b></div>
                <div style="margin-top: 10px; padding: 8px; border-radius: 6px; background-color: #FFFFFF; border: 1px solid #E5E7EB; text-align: center;">
                    <span style="font-weight: bold; color: {color}; font-size: 15px;">{status}</span>
                </div>
            </div>
            """
            
        report_html = f"""
        <div id="print-area" style="padding: 25px; border: 2px solid #1E3A8A; border-radius: 12px; font-family: 'Malgun Gothic', sans-serif; background-color: #FFFFFF; color: #333333; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="font-size: 12px; color: #1E3A8A; font-weight: bold; border: 1px solid #1E3A8A; padding: 3px 8px; border-radius: 20px;">천명의선택 NAVI</span>
                <h2 style="color: #1E3A8A; margin-top: 8px; margin-bottom: 5px; font-size: 24px;">수시 학생부종합전형 3대 희망대학 비교 분석 보고서</h2>
            </div>
            
            <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                <span style="font-size: 15px; font-weight: bold; color: #1E3A8A;">산출 내신 등급: </span>
                <span style="font-size: 20px; font-weight: bold; color: #EF4444;">{my_gpa} 등급</span>
            </div>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 12px;">선택한 3개 대학 및 학과 비교 진단</h3>
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; margin-bottom: 20px;">
                {cards_html}
            </div>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 8px; font-size: 16px; margin-bottom: 10px;">수험생 안내사항</h3>
            <div style="background-color: #F3F4F6; padding: 12px; border-radius: 8px; font-size: 13px; color: #4B5563;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>본 진단 평가는 학생부 교과 등급 및 전년도 합격자 컷 지표를 바탕으로 산출되었습니다.</li>
                    <li>학생부종합전형 특성상 세특 및 창체 등의 정성평가 요소에 따라 최종 합격 가능성은 변동될 수 있습니다.</li>
                </ul>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 15px;">
            <button onclick="window.print()" style="padding: 10px 24px; background-color: #1E3A8A; color: white; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer;">
                🖨️ 비교 보고서 PDF 저장 / 인쇄
            </button>
        </div>
        """
        
        st.markdown("### 📊 분석 및 비교 리포트")
        st.components.v1.html(report_html, height=600, scrolling=True)
