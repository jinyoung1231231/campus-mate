import streamlit as st
import google.generativeai as genai

# 1. API 키 설정 (금고 확인)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets 설정에 GEMINI_API_KEY가 없습니다.")
    st.stop()

st.title("🎓 캠퍼스 메이트 AI")

# 2. 모델 설정 (가장 표준적인 이름만 사용)
model = genai.GenerativeModel('gemini-1.5-flash')

user_input = st.text_input("AI에게 궁금한 점을 물어보세요!")

if st.button("질문하기"):
    if user_input:
        with st.spinner("AI가 응답을 생성 중입니다..."):
            try:
                # 옵션 없이 가장 기본적으로 호출
                response = model.generate_content(user_input)
                st.success("답변이 생성되었습니다!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"에러 발생: {e}")
                st.info("여전히 404 에러가 난다면, API 키를 다른 구글 계정으로 발급받아 보시는 것을 권장합니다.")
    else:
        st.warning("내용을 입력해주세요.")
