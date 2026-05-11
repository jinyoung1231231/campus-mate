import streamlit as st
import google.generativeai as genai

# 1. API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("금고(Secrets)에 키가 없습니다.")
    st.stop()

st.title("🎓 캠퍼스 메이트 AI (최종 해결 버전)")

# 2. 에러가 났던 이름을 버리고, 더 구체적인 모델 이름을 사용합니다.
# 현재 가장 안정적인 모델 이름 리스트입니다.
model_list = ['gemini-1.5-flash-latest', 'gemini-1.5-pro-latest']

user_input = st.text_input("질문을 입력하세요:")

if st.button("AI 질문하기"):
    if user_input:
        success = False
        with st.spinner("AI가 응답을 생성 중입니다..."):
            for m_name in model_list:
                try:
                    # 모델 초기화
                    model = genai.GenerativeModel(m_name)
                    # 응답 생성
                    response = model.generate_content(user_input)
                    st.success(f"연결 성공! (사용 모델: {m_name})")
                    st.markdown(response.text)
                    success = True
                    break # 성공하면 반복문 종료
                except Exception as e:
                    st.warning(f"{m_name} 모델 연결 시도 실패...")
                    continue
            
            if not success:
                st.error("모든 AI 모델 연결에 실패했습니다.")
                st.info("해결 방법: Google AI Studio에서 '새 프로젝트'로 API 키를 다시 발급받아 보세요.")
    else:
        st.warning("내용을 입력해주세요.")
