import streamlit as st
import google.generativeai as genai

# 1. API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets에 키가 없습니다.")
    st.stop()

st.title("🎓 캠퍼스 메이트 (정상 작동 테스트)")

# 2. 모델 설정
# models/ 를 붙이지 않는 것이 최신 라이브러리의 표준입니다.
model = genai.GenerativeModel('gemini-1.5-flash')

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    if user_input:
        with st.spinner("AI가 응답을 생성 중입니다..."):
            try:
                # 군더더기 없이 가장 기본 호출
                response = model.generate_content(user_input)
                st.success("연결 성공!")
                st.markdown(response.text)
            except Exception as e:
                # 만약 여기서 또 404가 나면, 현재 서버가 인식하는 모델이 뭔지 직접 확인합니다.
                st.error(f"에러 발생: {e}")
                try:
                    st.info("서버 인식 가능 모델 목록:")
                    models = [m.name for m in genai.list_models()]
                    st.write(models)
                except:
                    pass
    else:
        st.warning("질문을 입력해주세요.")
