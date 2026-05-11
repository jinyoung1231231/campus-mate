import streamlit as st
import google.generativeai as genai

# 금고에서 키 가져오기
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("Secrets에 GEMINI_API_KEY가 설정되지 않았습니다.")
except Exception as e:
    st.error(f"설정 불러오기 실패: {e}")

st.title("🎓 캠퍼스 메이트 (최종 점검)")

# 에러 해결을 위한 모델 강제 지정
# 1.5-flash가 안되면 1.0-pro라도 작동하게 시도합니다.
def get_response(prompt_text):
    for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt_text)
        except Exception:
            continue
    return None

user_input = st.text_input("질문을 입력하세요")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("AI가 응답을 생성 중입니다..."):
            response = get_response(user_input)
            if response:
                st.markdown(response.text)
            else:
                st.error("모든 AI 모델 연결에 실패했습니다. API 키의 활성화 상태를 다시 확인해주세요.")
