import streamlit as st
import google.generativeai as genai

# 1. 키 설정 (금고 확인)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("금고(Secrets)에 키가 없습니다!")

# 2. 모델 강제 지정 (가장 호환성 높은 이름)
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🎓 캠퍼스 메이트 테스트")

# 3. 아주 짧은 테스트 질문
if st.button("AI 연결 확인"):
    try:
        # 질문을 아주 짧게 보내서 응답이 오는지 확인
        response = model.generate_content("Hi")
        st.success("드디어 연결되었습니다!")
        st.write(response.text)
    except Exception as e:
        # 에러가 나면 숨기지 말고 다 보여달라고 설정
        st.error(f"연결 실패 이유: {e}")
