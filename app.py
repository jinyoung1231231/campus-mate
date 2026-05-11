import streamlit as st
import google.generativeai as genai

# 1. 제미나이 AI 설정 (발급받은 키 입력)
GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# 페이지 설정
st.set_page_config(page_title="캠퍼스 메이트", layout="wide")

# 사이드바: 내 정보 입력
with st.sidebar:
    st.header("👤 프로필")
    name = st.text_input("이름", "유진영")
    major = st.text_input("전공", "인문학부")
    interest = st.text_input("관심 분야", "기획, 마케팅, IT")
    st.success(f"{name}님, 환영합니다!")

st.title("🎓 캠퍼스 메이트: 진로 & 학점 AI 도우미")

# 메뉴 구성
tab1, tab2 = st.tabs(["🎯 AI 진로 내비게이션", "📚 AI 학점 도우미"])

# --- 탭 1: 진로 탐색 ---
with tab1:
    st.header("내 전공과 관심사에 맞는 진로 찾기")
    if st.button("진로 분석 시작"):
        with st.spinner("AI가 최적의 진로를 분석 중입니다..."):
            prompt = f"전공이 {major}이고 관심사가 {interest}인 대학생에게 어울리는 구체적인 직종 3개와 필요한 역량을 설명해줘."
            response = model.generate_content(prompt)
            st.markdown(response.text)

# --- 탭 2: 학점 도우미 ---
with tab2:
    st.header("강의 자료 기반 예상 문제 생성")
    user_input = st.text_area("강의 노트나 학습 내용을 입력하세요 (또는 공부 중인 주제)")
    
    if st.button("예상 문제 생성"):
        if user_input:
            with st.spinner("AI가 시험 문제를 출제 중입니다..."):
                prompt = f"다음 내용을 바탕으로 대학 시험 수준의 예상 문제 3개와 정답/해설을 만들어줘: {user_input}"
                response = model.generate_content(prompt)
                st.markdown("### 📝 AI 출제 예상 문제")
                st.write(response.text)
        else:
            st.warning("내용을 입력해 주세요!")
