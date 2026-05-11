import streamlit as st
import google.generativeai as genai

# API 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets에 키가 등록되지 않았습니다.")
    st.stop()

# 가장 안정적인 모델 경로 지정
model = genai.GenerativeModel('models/gemini-1.5-flash')

st.title("🎓 캠퍼스 메이트 AI")

user_input = st.text_input("궁금한 것을 물어보세요!")

if st.button("질문하기"):
    if user_input:
        with st.spinner("생각 중..."):
            try:
                response = model.generate_content(user_input)
                st.success("답변 완료!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
    else:
        st.warning("질문을 입력해 주세요.")
