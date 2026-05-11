import streamlit as st
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# 1. API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets에 키가 없습니다.")
    st.stop()

st.title("🎓 캠퍼스 메이트 (최종 해결)")

# 2. 모델 설정 및 통로(API 버전) 강제 지정
# 핵심: 'v1' 정식 버전을 사용하도록 강제 설정합니다.
model = genai.GenerativeModel('gemini-1.5-flash')

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("AI가 응답을 생성 중입니다..."):
            try:
                # request_options를 통해 v1beta가 아닌 정식 버전을 사용하도록 유도
                response = model.generate_content(
                    user_input,
                    request_options=RequestOptions(api_version='v1')
                )
                st.success("연결 성공!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"에러 발생: {e}")
                st.info("이 에러가 계속된다면, 구글 AI Studio에서 '새 프로젝트'로 키를 다시 발급받는 것이 유일한 해결책입니다.")
    else:
        st.warning("내용을 입력해주세요.")
