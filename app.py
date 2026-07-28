import streamlit as st
import pandas as pd
import re

# =====================================================================
# 1. 데이터 로드 및 자동 생성
# =====================================================================
def load_data():
    try:
        df = pd.read_csv("2026 수시정리.csv", encoding="utf-8-sig")
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
        df.to_csv("2026 수시정리.csv", index=False, encoding="utf-8-sig")
    return df

df = load_data()

# =====================================================================
# 2. 유연해진 학생부 텍스트 파싱 및 학년별 내신 계산 함수
# =====================================================================
def parse_student_record(text, target_grade=3):
    """
    텍스트 내 '[1학년]', '1학년' 형태의 헤더를 인식하여 학년별 과목을 분류합니다.
    학년 구분이 없는 경우 기본 1~2학년 또는 전체 성적으로 자동 할당합니다.
    """
    lines = text.split("\n")
    current_grade = 1  # 기본값
    parsed_subjects = []

    # 과목 추출용 유연한 정규식 (한글/숫자/문자 포함 과목명 지원)
    pattern = re.compile(r'([가-힣0-9IⅠⅡIII]+)\s*\(?(\d+)\s*단위\s*[\s/,\-_]*\s*(\d+)\s*등급\)?')

    for line in lines:
        line_str = line.strip()
        # 학년 헤더 감지
        if "1학년" in line_str or "[1" in line_str:
            current_grade = 1
        elif "2학년" in line_str or "[2" in line_str:
            current_grade = 2
        elif "3학년" in line_str or "[3" in line_str:
            current_grade = 3

        match = pattern.search(line_str)
        if match:
            sub_name = match.group(1)
            unit = int(match.group(2))
            rank = int(match.group(3))
            parsed_subjects.append({
                "학년": current_grade,
                "과목": sub_name,
                "단위": unit,
                "등급": rank
            })

    # 요청된 학년 이하의 성적만 필터링 (예: 2학년 선택 시 1,2학년만)
    filtered_subs = [s for s in parsed_subjects if s["학년"] <= target_grade]
    
    # 3학년 선택 시 3학년 데이터가 실제 존재하는지 확인
    has_3rd_grade = any(s["학년"] == 3 for s in parsed_subjects)

    total_rc = sum(s["등급"] * s["단위"] for s in filtered_subs)
    total_c = sum(s["단위"] for s in filtered_subs)
    
    gpa = round(total_rc / total_c, 2) if total_c > 0 else 0.0
    return gpa, filtered_subs, has_3rd_grade

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
# [STEP 1] 대학 및 전형 선택
# ---------------------------------------------------------------------
st.markdown('<div class="step-box"><b>[STEP 1] 목표 대학 및 전형 선택</b></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    region_list = sorted(df["지역"].unique())
    selected_region = st.selectbox("지역 선택", region_list)

    univ_list = sorted(df[df["지역"] == selected_region]["대학"].unique())
    selected_univ = st.selectbox("대학 선택", univ_list)

with col2:
    dept_list = sorted(df[(df["지역"] == selected_region) & (df["대학"] == selected_univ)]["학과"].unique())
    selected_dept = st.selectbox("학과 선택", dept_list)

    target_row = df[(df["지역"] == selected_region) & (df["대학"] == selected_univ) & (df["학과"] == selected_dept)].iloc[0]
    selected_type = st.text_input("전형명", value=target_row["전형"], disabled=True)

# ---------------------------------------------------------------------
# [STEP 2] 학년 선택 및 학생부 입력
# ---------------------------------------------------------------------
st.markdown('<div class="step-box"><b>[STEP 2] 학년 설정 및 학생부 성적 입력</b></div>', unsafe_allow_html=True)

# [요청 1] 학년 지정 버튼 (라디오 단추)
selected_grade = st.radio(
    "📌 분석할 대상 학년을 선택하세요:",
    options=[1, 2, 3],
    format_func=lambda x: f"{x}학년 기준 반영",
    index=2,
    horizontal=True
)

uploaded_file = st.file_uploader("학생부 텍스트 파일(.txt)을 업로드해 주세요.", type=["txt"])

# 학년 구분이 명확한 샘플 텍스트
sample_record_text = """[1학년]
국어 (4단위/2등급)
수학 (4단위/1등급)
영어 (4단view/2등급)
[2학년]
화학Ⅰ (3단위/1등급)
생명과학Ⅰ (3단위/2등급)
화학Ⅱ (3단위/2등급)
생명과학Ⅱ (3단위/1등급)
"""

use_sample = st.checkbox("샘플 1~2학년 데이터로 테스트하기")

record_text = ""
if uploaded_file is not None:
    record_text = uploaded_file.read().decode("utf-8")
elif use_sample:
    record_text = sample_record_text
    st.info("💡 1, 2학년 성적만 포함된 샘플 데이터가 로드되었습니다.")

# ---------------------------------------------------------------------
# [STEP 3] 분석 실행 및 3학년 임의성적 가상 시뮬레이션
# ---------------------------------------------------------------------
if record_text:
    # 파싱 수행
    my_gpa, parsed_sub, has_3rd = parse_student_record(record_text, target_grade=selected_grade)
    
    # [요청 2] 3학년 선택 + 3학년 성적 부재 시 안내
    if selected_grade == 3 and not has_3rd:
        st.warning("⚠️ 입력된 데이터에 3학년 성적이 없습니다. 현재 보유된 **1~2학년 성적만으로 산출**된 내신 수치를 보여줍니다.")
        
        # [요청 3] 3학년 임의 성적 적용 시뮬레이션 버튼
        if st.checkbox("🔮 3학년 임의 성적(예: 12단위 / 1.5등급)을 추가하여 전체 등급 시뮬레이션하기"):
            # 가상 3학년 과목 추가
            virtual_3rd_sub = {"학년": 3, "과목": "3학년_가상성적(주요교과)", "단위": 12, "등급": 1.5}
            parsed_sub.append(virtual_3rd_sub)
            
            # 재계산
            total_rc = sum(s["등급"] * s["단위"] for s in parsed_sub)
            total_c = sum(s["단위"] for s in parsed_sub)
            my_gpa = round(total_rc / total_c, 2)
            st.success(f"✅ 3학년 가상 성적이 포함된 **3학년 전체 최종 환산 내신: {my_gpa} 등급**")

    if st.button("학생부 정밀 분석 및 보고서 출력", type="primary"):
        cut_50 = target_row["50%컷"]
        cut_70 = target_row["70%컷"]
        req_subjects = [s.strip() for s in target_row["필수과목"].split(",")]
        
        # 필수과목 이수 여부 체크
        passed_subjects = []
        missing_subjects = []
        for req in req_subjects:
            if any(req in sub["과목"] for sub in parsed_sub):
                passed_subjects.append(req)
            else:
                missing_subjects.append(req)
                
        # 예측 로직
        if my_gpa <= cut_50:
            status = "안정 (합격 유력)"
            color = "#10B981"
        elif my_gpa <= cut_70:
            status = "적정 (경쟁력 있음)"
            color = "#3B82F6"
        else:
            status = "소신 (내신 보완 필요)"
            color = "#EF4444"
            
        # HTML 보고서 생성
        report_html = f"""
        <div id="print-area" style="padding: 30px; border: 2px solid #1E3A8A; border-radius: 12px; font-family: 'Malgun Gothic', sans-serif; background-color: #FFFFFF; color: #333333; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 25px;">
                <span style="font-size: 12px; color: #1E3A8A; font-weight: bold; border: 1px solid #1E3A8A; padding: 3px 8px; border-radius: 20px;">AI 입시 분석 시스템</span>
                <h1 style="color: #1E3A8A; margin-top: 10px; margin-bottom: 5px; font-size: 28px;">수시 정밀 진단 보고서</h1>
                <p style="color: #6B7280; font-size: 14px; margin: 0;">선택 기준: <strong>{selected_grade}학년 기준 반영</strong></p>
            </div>
            
            <hr style="border: 0; height: 1px; background: #E5E7EB; margin-bottom: 25px;">
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                <tr style="background-color: #F3F4F6;">
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">지원 구분</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">{selected_univ} - {selected_dept}</td>
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">전형명</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">{selected_type}</td>
                </tr>
                <tr>
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">산출 내신 등급</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #EF4444; font-size: 18px;">{my_gpa} 등급</td>
                    <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">전년도 입결 컷</th>
                    <td style="border: 1px solid #D1D5DB; padding: 10px; text-align: center; font-size: 13px;">50%: {cut_50} | 70%: {cut_70}</td>
                </tr>
            </table>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 10px; margin-bottom: 15px;">1. 진단 결과</h3>
            <div style="background-color: #F9FAFB; border: 1px solid #E5E7EB; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 25px;">
                <span style="font-size: 16px; font-weight: bold;">예측 상태: </span>
                <span style="font-size: 22px; font-weight: bold; color: {color};">{status}</span>
            </div>

            <h3 style="color: #1E3A8A; border-left: 4px solid #1E3A8A; padding-left: 10px; margin-bottom: 15px;">2. 권장 과목 충족 상황</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                <thead>
                    <tr style="background-color: #F3F4F6;">
                        <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">구분</th>
                        <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">과목명</th>
                        <th style="border: 1px solid #D1D5DB; padding: 10px; text-align: center;">상태</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #10B981;'>이수</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center;'>{sub}</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #10B981;'>★ 충족</td></tr>" for sub in passed_subjects])}
                    {"".join([f"<tr><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #EF4444;'>미이수</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center;'>{sub}</td><td style='border: 1px solid #D1D5DB; padding: 10px; text-align: center; color: #EF4444;'>⚠️ 미충족</td></tr>" for sub in missing_subjects])}
                </tbody>
            </table>
        </div>
        """
        st.components.v1.html(report_html, height=650, scrolling=True)
