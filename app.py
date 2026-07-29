import os
import math
import re
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
import google.generativeai as genai

# ==========================================
# 0. 페이지 기본 설정 및 디자인
# ==========================================
st.set_page_config(
    page_title="천명의선택 학생부 NAVI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (UI/UX 개선 및 반응형 디자인)
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
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #F1F5F9;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #38BDF8;
        padding-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. API 키 자동 로드 로직 (구글 Gemini)
# ==========================================
AUTO_GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# ==========================================
# 2. 초기화 상태 관리 (세션 안전성 확보)
# ==========================================
if 'reset_count' not in st.session_state:
    st.session_state.reset_count = 0

if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None

if 'gpa_data' not in st.session_state:
    st.session_state.gpa_data = None

def force_reset():
    """세션 상태를 완전히 초기화하는 안전한 리셋 함수"""
    for key in list(st.session_state.keys()):
        if key != 'reset_count':
            del st.session_state[key]
    st.session_state.reset_count += 1
    st.rerun()

# ==========================================
# 3. 데이터 파싱 함수 (HTML / TXT 범용 지원)
# ==========================================
def parse_student_record(file_content, is_html=True):
    """
    학생부 파일에서 교과 성적 및 세부능력 및 특기사항(세특)을 정교하게 추출합니다.
    """
    subjects = []
    activities_text = ""

    if is_html:
        soup = BeautifulSoup(file_content, 'html.parser')
        # 전체 텍스트 추출 (자연어 분석 및 세특 키워드 추출용)
        activities_text = soup.get_text(separator="\n")

        # 성적 테이블 파싱 시도 (나이스 표준 테이블 매칭 패턴)
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                # 성적 구조 [교과, 과목, 단위수, 원점수, 과목평균, 표준편차, 석차등급] 형태 탐색
                if len(cols) >= 5:
                    unit_match = re.search(r'\d+', cols[2]) if len(cols) > 2 else None
                    grade_match = re.search(r'\d+', cols[-1]) if len(cols) > 0 else None
                    
                    if unit_match and grade_match:
                        try:
                            unit = int(unit_match.group())
                            grade = int(grade_match.group())
                            if 1 <= grade <= 9:  # 유효한 석차등급 범위 검증
                                subject_name = cols[1]
                                subjects.append({"subject": subject_name, "unit": unit, "grade": grade})
                        except ValueError:
                            pass
    else:
        # 일반 텍스트 파일 처리
        activities_text = file_content
        # 정규식을 이용해 "과목명 [단위수] 등급" 형태의 패턴 매칭 시도
        pattern = r'([가-힣a-zA-Z0-9\s]+)\s*\[(\d+)단위\]\s*(\d+)등급'
        matches = re.findall(pattern, file_content)
        for match in matches:
            try:
                subjects.append({
                    "subject": match[0].strip(),
                    "unit": int(match[1]),
                    "grade": int(match[2])
                })
            except ValueError:
                pass

    df_gpa = pd.DataFrame(subjects) if subjects else pd.DataFrame(columns=["subject", "unit", "grade"])
    return df_gpa, activities_text

# ==========================================
# 4. 학과별 핵심 키워드 사전 및 매칭 알고리즘
# ==========================================
MAJOR_KEYWORDS = {
    "컴퓨터교육과/컴퓨터공학과": ["컴퓨터", "정보", "교육", "코딩", "프로그래밍", "알고리즘", "수업", "교사", "디지털", "소프트웨어", "AI", "인공지능", "데이터"],
    "디자인학과": ["디자인", "시각", "공간", "제품", "창의", "조형", "색채", "그래픽", "사용자", "콘텐츠", "미술", "UX/UI"],
    "회화과": ["회화", "미술", "예술", "표현", "창작", "색채", "재료", "작가", "작품", "전시", "드로잉", "유화"],
    "음악학과": ["음악", "연주", "작곡", "이론", "예술", "악기", "성악", "음향", "창작", "감상", "클래식", "오케스트라"],
    "체육학과": ["체육", "운동", "스포츠", "건강", "생리", "훈련", "지도", "신체", "역학", "교육", "트레이닝"],
    "연극영화과": ["연극", "영화", "영상", "연기", "연출", "시나리오", "제작", "카메라", "무대", "예술", "시네마", "대본"]
}

def calculate_keyword_score(text, keywords):
    """학생부 내 전공 적합성 키워드의 빈도를 분석합니다."""
    if not text:
        return 0, []
    matched = []
    score = 0
    for kw in keywords:
        count = len(re.findall(re.escape(kw), text))
        if count > 0:
            matched.append((kw, count))
            score += count
    return score, sorted(matched, key=lambda x: x[1], reverse=True)

# ==========================================
# 5. 메인 레이아웃 및 웹 인터페이스 구성
# ==========================================
st.markdown('<div class="main-header">🧭 천명의선택 학생부 NAVI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI 기반 학생부 종합 분석 및 전공 적합성 진단 프로그램</div>', unsafe_allow_html=True)

# 사이드바 패널
with st.sidebar:
    st.header("⚙️ 설정 및 입력")
    
    # 1. API 키 검증 및 입력 구조 보안 강화
    api_key = AUTO_GEMINI_API_KEY
