import streamlit as st
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.services.generative_service import client

# 1. API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets에 키가 없습니다.")
    st.stop()

st.title("🎓 캠퍼스 메이트 (최종 강제 연결)")

# 2. 모델 설정 (이름을 가장 표준적인 것으로 고정)
model = genai.GenerativeModel('gemini-1.5-flash')

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("강제 연결 시도 중..."):
            try:
                # [핵심] v1beta 에러를 피하기 위해 정식 버전(v1) 통로를 강제 지정합니다.
                from google.generativeai.types import RequestOptions
                response = model.generate_content(
                    user_input,
                    request_options=RequestOptions(api_version='v1')
                )
                st.success("드디어 연결 성공!")
                st.markdown(response.text)
            except Exception as e:
                # 만약 여기서도 에러가 나면, 서버가 인식하는 진짜 모델 목록을 출력해버립니다.
                st.error(f"에러 발생: {e}")
                if "404" in str(e):
                    st.info("현재 서버에서 인식 가능한 모델 목록을 확인합니다...")
                    available_models = [m.name for m in genai.list_models()]
                    st.write("사용 가능한 모델:", available_models)
    else:
        st.warning("내용을 입력해주세요.")
