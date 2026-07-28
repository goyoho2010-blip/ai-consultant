import streamlit as st
import pandas as pd
import re

# =====================================================================
# 1. 데이터 로드 및 열 이름 유연한 처리
# =====================================================================
def load_data():
    try:
        # CSV 파일 읽기
        df = pd.read_csv("2026 수시정리.csv", encoding="utf-8-sig")
        
        # 열 이름 표준화 (실제 파일 이름 -> 코드 내부용 이름)
        column_mapping = {
            "대학명": "대학",
            "학과명": "학과",
            "전형명": "전형",
            "2025등급컷2": "50%컷",
            "2025등급컷": "70%컷"
        }
        df = df.rename(columns=column_mapping)
        
        # 필수 열 존재 여부 체크 후 없는 열은 기본값 추가
        if "필수과목" not in df.columns:
            df["필수과목"] = ""
            
        # 주요 열에 빈칸이 있는 행 제거
        df = df.dropna(subset=["지역", "대학", "학과"])
        
    except FileNotFoundError:
        # 파일이 없을 경우 자동 생성할 샘플 데이터
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
        df.to_csv("2026 수시정리.csv", index=False, encoding="utf-8-sig")
        
    return df

df = load_data()

# =====================================================================
# 2. 학생부 텍스트 파싱 및 내신 계산 함수
# =====================================================================
def parse_student_record(text):
    # 패턴 예시: 국어 (3단위/1등급) 또는 수학 4단위 2등급 등 유연한 매칭
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
# 3. Streamlit 웹 UI 구성
# =====================================================================
st.set_page_config(page_title="AI 입시 컨설팅 시스템", layout="centered")

st.markdown("""
    <style>
    .main-title {font-size: 32px; font-weight: bold; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .sub-title {font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .step-box {background-color: #F3F4F6; padding: 15px; border-radius: 8px; border-left: 5px solid #1E3A8A; margin-bottom: 20px;}
    </style>
    <div class="main-title">🎓 AI 입시 컨설팅 시스템</div>
    <div class="sub-title">2026학년도 학생부종합전형 정밀 진단 및 합격 예측 시뮬레이터</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# [STEP 1] 대학 및 전형 선택 조건 설정
# ---------------------------------------------------------------------
st.markdown('<div class="step-box"><b>[STEP 1] 목표 대학 및 전형 선택</b></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    region_list = sorted(df["지역"].astype(str).unique())
    selected_region = st.selectbox("지역 선택", region_list)

    univ_list = sorted(df[df["지역"] == selected_region]["대학"].astype(str).unique())
    selected_univ = st.selectbox("대학 선택", univ_list)

with col2:
    dept_list = sorted(df[(df["지역"] == selected_region) & (df["대학"] == selected_univ)]["학과"].astype(str).unique())
    selected_dept = st.selectbox("학과 선택", dept_list)

    target_df = df[(df["지역"] == selected_region) & (df["대학"] == selected_univ) & (df["학과"] == selected_dept)]
    
    # 동일 대학/학과에 여러 전형이 있을 수 있으므로 선택 가능하게 처리
    type_list = sorted(target_df["전형"].astype(str).unique())
    selected_type = st.selectbox("전형 선택", type_list)
    
    target_row = target_df[target_df["전형"] == selected_type].iloc[0]

# ---------------------------------------------------------------------
# [STEP 2] 학생부 업로드 대기 화면
# ---------------------------------------------------------------------
st.markdown('<div class="step-box"><b>[STEP 2] 학생부를 업로드하세요</b></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("학생부 텍스트 파일(.txt)을 업로드해 주세요.", type=["txt"])

# 테스트 편의를 위한 샘플 텍스트 기본값 제공
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
    record_text = uploaded_file.read().decode("utf-8")
elif use_sample:
    record_text = sample_record_text
    st.info("샘플 텍스트가 적용되었습니다. 아래 '학생부 정밀 분석 시작' 버튼을 누르세요.")

# ---------------------------------------------------------------------
# [STEP 3] 결과 도출 및 PDF 인쇄 보고서 생성
# ---------------------------------------------------------------------
if record_text:
    if st.button("학생부 정밀 분석 시작", type="primary"):
        my_gpa, parsed_sub = parse_student_record(record_text)
        
        # 컷 데이터 숫자로 안전 변환
        try:
            cut_50 = float(target_row["50%컷"])
        except (ValueError, TypeError):
            cut_50 = 9.0
            
        try:
            cut_70 = float(target_row["70%컷"])
        except (ValueError, TypeError):
            cut_70 = 9.0
        
        # 필수과목 문자열 파싱
        raw_subjects = str(target_row["필수과목"]) if pd.notna(target_row["필수과목"]) else ""
        req_subjects = [s.strip() for s in raw_subjects.split(",")] if raw_subjects else []
        
        # 필수과목 이수 여부 체크
        passed_subjects = []
        missing_subjects = []
        for req in req_subjects:
            if not req:
                continue
            if any(req in sub["과목"] for sub in parsed_sub):
                passed_subjects.append(req)
            else:
                missing_subjects.append(req)
                
        # 합격 예측 로직
        if my_gpa <= cut_50 and cut_50 != 9.0:
            status = "안정 (합격 유력)"
            color = "#10B981"
        elif my_gpa <= cut_70 and cut_70 != 9.0:
            status = "적정 (경쟁력 있음)"
            color = "#3B82F6"
        else:
            status = "소신 (내신 보완 필요)"
            color = "#EF4444"
            
        # HTML 기반 프리미엄 보고서 생성
        report_html = f"""
        <div id="print-area" style="padding: 30px; border: 2px solid #1E3A8A; border-radius: 12px; font-family: 'Malgun Gothic', sans-serif; background-color: #FFFFFF; color: #333333; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 25px;">
                <span style="font-size: 12px; color: #1E3A8A; font-weight: bold; border: 1px solid #1E3A8A; padding: 3px 8px; border-radius: 20px;">AI IP-PORTFOLIO</span>
                <h1 style="color: #1E3A8A; margin-top: 10px; margin-bottom: 5px; font-size: 28px;">수시 학생부종합전형 정밀 진단 보고서</h1>
                <p style="color: #6B7280; font-size: 14px; margin: 0;">본 결과지는 브라우저 인쇄 기능을 통해 PDF로 즉시 저장 및 출력할 수 있습니다.</p>
            </div>
            
            <hr style="border: 0; height: 1px; background: #E5E7EB; margin-bottom: 25px;">
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                <tr style="background-color: #F3F4F6;">
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">지원 구분</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">{selected_univ} - {selected_dept}</td>
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">적용 전형</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">{selected_type}</td>
                </tr>
                <tr>
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">산출 내신 등급</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #EF4444; font-size: 18px;">{my_gpa} 등급</td>
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">전년도 합격 컷</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-size: 13px;">50% 컷: {cut_50 if cut_50 != 9.0 else '정보없음'} | 70% 컷: {cut_70 if cut_70 != 9.0 else '정보없음'}</td>
                </tr>
            </table>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 10px; margin-bottom: 15px;">1. 합격 가능성 진단 결과</h3>
            <div style="background-color: #F9FAFB; border: 1px solid #E5E7EB; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 25px;">
                <span style="font-size: 16px; font-weight: bold;">최종 예측 결과: </span>
                <span style="font-size: 22px; font-weight: bold; color: {color};">{status}</span>
                <p style="margin-top: 10px; font-size: 14px; color: #4B5563;">
                    목표 학과의 전년도 입시 결과(70% 컷) 대비 내신 등급 우수성을 기준으로 산출된 정량적 지표입니다.
                </p>
            </div>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 10px; margin-bottom: 15px;">2. 핵심 권장 과목 이수 현황</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                <thead>
                    <tr style="background-color: #F3F4F6;">
                        <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">구분</th>
                        <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">과목명</th>
                        <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">충족 여부</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #10B981; font-weight: bold;'>이수 완료</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center;'>{sub}</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #10B981;'>★ 충족</td></tr>" for sub in passed_subjects])}
                    {"".join([f"<tr><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #EF4444; font-weight: bold;'>미이수 과목</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center;'>{sub}</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #EF4444;'>⚠️ 미충족</td></tr>" for sub in missing_subjects])}
                    {"<tr><td colspan='3' style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #6B7280;'>설정된 필수 과목이 없습니다.</td></tr>" if not req_subjects else ""}
                </tbody>
            </table>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 10px; margin-bottom: 15px;">3. 수험생 맞춤형 종합 가이드</h3>
            <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; padding: 15px; border-radius: 8px; font-size: 14px; color: #1E40AF;">
                <ul>
                    <li>본 진단 평가는 정량적 내신 및 필수 교과 이수 여부만을 기준으로 정밀 계산되었습니다.</li>
                    <li>학생부종합전형의 특성상 세부능력 및 특기사항(세특), 창의적 체험활동 등 정성 평가 요소에 따라 실질 결과는 달라질 수 있습니다.</li>
                    <li>미이수 권장 과목이 있는 경우 면접이나 자기소개서(제출 시) 등에서 해당 학문 분야에 대한 관심과 보완 노력을 적극 피력해야 합니다.</li>
                </ul>
            </div>
        </div>
        
        <!-- 브라우저 인쇄 트리거 버튼 -->
        <div style="text-align: center; margin-top: 20px;">
            <button onclick="window.print()" style="padding: 12px 30px; background-color: #1E3A8A; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                🖨️ PDF 리포트 인쇄 및 저장하기
            </button>
        </div>
        """
        
        st.markdown("### 📊 분석 리포트")
        st.components.v1.html(report_html, height=750, scrolling=True)
      
      
