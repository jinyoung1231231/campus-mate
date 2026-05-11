import streamlit as st
import google.generativeai as genai

# 1. API 키 설정 (금고 확인)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets 설정에 GEMINI_API_KEY가 없습니다.")
    st.stop()

st.title("🎓 캠퍼스 메이트 AI (환경 최신화 버전)")

# 2. 모델 설정
# 버전 문제를 피하기 위해 가장 최신 엔진(v1)을 사용하도록 유도
model = genai.GenerativeModel('gemini-1.5-flash')

user_input = st.text_input("질문을 입력하세요 (예: 안녕?)")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("AI가 응답을 생성 중입니다..."):
            try:
                # 작동 확인을 위한 호출
                response = model.generate_content(user_input)
                st.success("연결 성공!")
                st.markdown(response.text)
            except Exception as e:
                # 만약 여기서 또 에러가 나면 상세 메시지를 출력합니다.
                st.error(f"에러 발생: {e}")
                st.info("해결 팁: GitHub의 requirements.txt 파일에 'google-generativeai>=0.8.3'이 적혀 있는지 확인해 주세요.")
