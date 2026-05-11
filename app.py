import streamlit as st
import google.generativeai as genai

# 1. API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets 설정 확인 필요")
    st.stop()

st.title("🎓 캠퍼스 메이트 (드디어 연결!)")

# 2. 서버 목록에서 확인된 최신 모델로 변경
# 1.5-flash 대신 목록에 있는 2.0-flash를 사용합니다.
model = genai.GenerativeModel('gemini-2.0-flash')

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("최신 모델로 답변 생성 중..."):
            try:
                response = model.generate_content(user_input)
                st.success("연결 성공!")
                st.markdown(response.text)
            except Exception as e:
                # 만약 2.0도 안된다면 가장 최신인 3.1-flash-lite로 시도
                try:
                    alt_model = genai.GenerativeModel('gemini-3.1-flash-lite')
                    response = alt_model.generate_content(user_input)
                    st.success("3.1 모델로 연결 성공!")
                    st.markdown(response.text)
                except Exception as e2:
                    st.error(f"최종 에러: {e2}")
    else:
        st.warning("내용을 입력해주세요.")
