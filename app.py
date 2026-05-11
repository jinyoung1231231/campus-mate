import streamlit as st
import google.generativeai as genai

# 1. 키 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. 모델 설정 (앞에 models/ 같은 거 다 떼고 이름만!)
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🎓 캠퍼스 메이트 (제발 되라!)")

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    try:
        response = model.generate_content(user_input)
        st.write(response.text)
    except Exception as e:
        st.error(f"에러 메시지: {e}")
