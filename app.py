import streamlit as st
import google.generativeai as genai

# 금고 확인
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets 설정 확인 필요")
    st.stop()

# 가장 안전하고 표준적인 모델 호출 (latest나 v1beta 언급 없이)
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🎓 캠퍼스 메이트 최종 테스트")

user_input = st.text_input("아무 글자나 입력 후 버튼을 누르세요")

if st.button("연결 테스트"):
    try:
        # 모델명 앞에 models/ 를 붙이지 않고 호출
        response = model.generate_content(user_input)
        st.success("연결 성공!")
        st.write(response.text)
    except Exception as e:
        st.error(f"최종 에러 메시지: {e}")
