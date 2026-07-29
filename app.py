import re
from bs4 import BeautifulSoup
import pandas as pd

def parse_neis_grade_html(html_content):
    """
    나이스(NEIS) 생활기록부 HTML에서 성적 데이터를 정확하게 파싱하는 함수
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    records = []
    
    # 성적 관련 테이블 찾기
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue
        
        # 헤더 파싱하여 컬럼 위치 식별
        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        
        # 교과, 과목, 단위수(학점), 석차등급 컬럼 인덱스 찾기
        idx_subject = -1
        idx_units = -1
        idx_grade = -1
        idx_term = -1
        
        for i, h in enumerate(headers):
            if '과목' in h or '교과목' in h:
                idx_subject = i
            elif '단위' in h or '학점' in h or '시수' in h:
                idx_units = i
            elif '석차등급' in h or '등급' in h:
                idx_grade = i
            elif '학기' in h:
                idx_term = i

        # 교과 성적 테이블이 아닌 경우 스킵
        if idx_units == -1 or idx_grade == -1:
            continue

        current_grade_level = "1학년" # 기본값 설정 또는 테이블 상단 텍스트 추적
        
        for row in rows[1:]:
            cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if len(cols) <= max(idx_units, idx_grade):
                continue
            
            # 단위수(시수) 및 석차등급 텍스트 추출
            unit_text = cols[idx_units]
            grade_text = cols[idx_grade]
            subject_name = cols[idx_subject] if idx_subject != -1 else "기타"
            
            # 숫자 정규화 추출
            unit_match = re.search(r'\d+', unit_text)
            grade_match = re.search(r'([1-9])등급?|([1-9])', grade_text)
            
            if unit_match and grade_match:
                units = float(unit_match.group(0))
                # 등급이 P/F이거나 성취도 평가(A,B,C)인 경우 제외 (석차등급 1~9등급만 추출)
                grade_val = float(grade_match.group(1) if grade_match.group(1) else grade_match.group(2))
                
                # 시수가 정상 범위(1~6 사이)인지 검증 (오파싱 방지)
                if 1 <= units <= 8 and 1 <= grade_val <= 9:
                    # 학기 식별 (테이블 구조 또는 행 내 정보 활용)
                    term_info = cols[idx_term] if idx_term != -1 and idx_term < len(cols) else "1학기"
                    
                    records.append({
                        '학년_학기': term_info, # 예: '1-1', '1-2', '2-1' 등
                        '과목': subject_name,
                        '시수': units,
                        '등급': grade_val
                    })

    return pd.DataFrame(records)


def calculate_custom_gpa(df):
    """
    유저 지정 공식 적용:
    1) 학기별/학년별 (등급 * 시수) 합 / 시수 총합 = 학기별 평균등급
    2) (성적이 있는 각 학기/학년별 평균등급의 합) / (성적이 산출된 총 학기/학년 수)
    """
    if df.empty:
        return 0.0, {}

    # 교과군 구분을 위한 과목 분류
    def classify_subject(name):
        if any(k in name for k in ['국어', '문학', '독서', '화작', '언매']):
            return '국어'
        elif any(k in name for k in ['수학', '수1', '수2', '미적', '기하', '확통']):
            return '수학'
        elif any(k in name for k in ['영어', '영문']):
            return '영어'
        elif any(k in name for k in ['사회', '역사', '한국사', '지리', '윤리', '일반사회', '정치', '경제']):
            return '사회'
        elif any(k in name for k in ['과학', '물리', '화학', '생명', '지구']):
            return '과학'
        return '기타'

    df['교과군'] = df['과목'].apply(classify_subject)

    # -------------------------------------------------------------
    # 1. 학기/학년 그룹별로 (등급 * 시수) 가중치 합 산출
    # -------------------------------------------------------------
    def get_term_gpa(sub_df):
        if sub_df.empty:
            return None
        
        # 학기/학년 단위 그룹화
        grouped = sub_df.groupby('학년_학기')
        term_averages = []
        
        for term, group in grouped:
            total_weighted_grade = (group['등급'] * group['시수']).sum()
            total_units = group['시수'].sum()
            
            if total_units > 0:
                term_avg = total_weighted_grade / total_units
                term_averages.append(term_avg)
                
        # 2. 성적이 있는 학기/학년 개수로 산술 평균
        if not term_averages:
            return 0.0
        
        final_gpa = sum(term_averages) / len(term_averages)
        return round(final_gpa, 2)

    # 전체 및 주요 교과군별 계산
    overall_gpa = get_term_gpa(df)
    
    # 국영수과사 교과군 필터링
    df_korean_eng_math_sci_soc = df[df['교과군'].isin(['국어', '영어', '수학', '과학', '사회'])]
    df_korean_eng_soc = df[df['교과군'].isin(['국어', '영어', '사회'])]
    df_math_sci = df[df['교과군'].isin(['수학', '과학'])]
    
    results = {
        '전과목 평균': overall_gpa,
        '국영수과사 평균': get_term_gpa(df_korean_eng_math_sci_soc),
        '국영수과 평균': get_term_gpa(df[df['교과군'].isin(['국어', '영어', '수학', '과학'])]),
        '국영사 평균': get_term_gpa(df_korean_eng_soc),
        '수학+과학 평균': get_term_gpa(df_math_sci)
    }
    
    return results

# --- 실행 예시 ---
# html_data = open("박경필 나이스+.html", "r", encoding="utf-8").read()
# df_parsed = parse_neis_grade_html(html_data)
# gpa_results = calculate_custom_gpa(df_parsed)
# print(gpa_results)
