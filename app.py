import streamlit as st
import google.generativeai as genai

# 1. 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets에 키가 없습니다.")
    st.stop()

# 2. 에러가 났던 'v1beta' 문제를 피하기 위해 모델명을 명확히 지정
# 'gemini-1.5-flash' 대신 아래 이름을 사용해 보세요.
MODEL_NAME = 'models/gemini-1.5-flash'

try:
    model = genai.GenerativeModel(model_name=MODEL_NAME)
except Exception as e:
    st.error(f"모델 초기화 에러: {e}")

st.title("🎓 캠퍼스 메이트 AI")

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("AI가 응답을 생성 중입니다..."):
            try:
                # 작동 여부를 확인하기 위한 가장 안전한 호출 방식
                response = model.generate_content(user_input)
                st.markdown(response.text)
            except Exception as e:
                # 여기서 또 404가 난다면 다른 모델로 자동 전환 시도
                st.warning("기본 모델 연결 실패. 대체 모델로 시도합니다...")
                try:
                    alt_model = genai.GenerativeModel('gemini-pro')
                    response = alt_model.generate_content(user_input)
                    st.markdown(response.text)
                except Exception as e2:
                    st.error(f"최종 연결 실패: {e2}")
    else:
        st.warning("내용을 입력해주세요.")
