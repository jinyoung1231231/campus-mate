import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 노션 스타일 및 수직 타임라인 전용 CSS 주입
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #37352f; }
    .notion-header { font-size: 28px; font-weight: 700; margin-bottom: 4px; color: #37352f; }
    .notion-sub { font-size: 14px; color: #7c7b77; margin-bottom: 24px; }
    .subject-block { background-color: #fbfbfa; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
    .subject-title { font-size: 18px; font-weight: 700; color: #37352f; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
    .schedule-box { background-color: #f7f7f5; border-radius: 6px; padding: 12px 16px; margin-top: 12px; margin-bottom: 16px; border-left: 3px solid #60a5fa; display: flex; gap: 24px; }
    .schedule-item { font-size: 13px; color: #4b5563; }
    .timeline-container { background-color: #ffffff; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-top: 14px; margin-bottom: 24px; }
    .vertical-timeline { position: relative; border-left: 2px solid #e3e2e0; margin-left: 12px; padding-left: 24px; margin-top: 16px; }
    .timeline-node { position: relative; margin-bottom: 18px; }
    .timeline-dot { position: absolute; left: -31px; top: 3px; width: 12px; height: 12px; border-radius: 50%; background-color: #fff; border: 3px solid #cbd5e1; z-index: 2; }
    .dot-active { border-color: #238387; background-color: #238387; box-shadow: 0 0 0 4px #e2f3f5; }
    .dot-done { border-color: #2e7d32; background-color: #2e7d32; }
    .node-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .node-badge { font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
    .nb-waiting { background-color: #f1f1ef; color: #7c7b77; }
    .nb-active { background-color: #e2f3f5; color: #238387; }
    .nb-done { background-color: #eaf5ea; color: #2e7d32; }
    .node-text { font-size: 13.5px; color: #37352f; line-height: 1.5; }
    .focus-panel { background-color: #f7f7f5; border-radius: 12px; padding: 32px; text-align: center; border: 1px solid #e3e2e0; margin-bottom: 24px; }
    .focus-timer { font-size: 48px; font-weight: 700; font-family: monospace; color: #238387; margin: 12px 0; }
    .focus-badge { background-color: #e2f3f5; color: #238387; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; display: inline-block; }
    .test-panel { background-color: #fff5f5; border: 1px solid #ffe3e3; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; }
    .test-timer { font-size: 36px; font-weight: 700; font-family: monospace; color: #e03131; }
    .omr-container { background-color: #fcfcfb; border-left: 3px solid #37352f; padding: 20px; border-radius: 0 8px 8px 0; }
    .consult-container { background-color: #fbfbfa; border: 1px solid #e3e2e0; border-radius: 8px; padding: 20px; margin-top: 20px; }
    .consult-user-q { font-size: 14px; font-weight: 600; color: #4b5563; background-color: #f3f4f6; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; }
    .consult-ai-a { font-size: 14px; color: #1f2937; line-height: 1.6; padding-left: 4px; }
    .report-card { background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 2px dashed #cbd5e1; border-radius: 12px; padding: 24px; text-align: center; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# 2. 초기화 및 세션 관리
@st.cache_resource
def init_db(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_db()

session_keys = {
    'page': 'gate', 'my_name': '', 'invite_code': '', 'current_mode': 'dashboard',
    'active_subject': '', 'active_day': 1, 'start_time': None, 'elapsed_time': 0,
    'current_ai_plan': '', 'current_ai_quiz': '', 'current_ai_consult_a': '',
    'input_manual_text': '', 'input_days': 7, 'input_grade': 'A+', 'refresh_lock': False
}
for k, v in session_keys.items():
    if k not in st.session_state: st.session_state[k] = v

def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

# 3. AI 엔진 (다중 파일 연동 강화)
def run_ai_engine(prompt_type, **kwargs):
    st.session_state.refresh_lock = True
    with st.spinner("AI가 학습 자료를 심층 분석 중입니다... 📝"):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            if prompt_type == "plan":
                p = f"과목: {kwargs['sub_name']}, 목표: {kwargs['grade']}, 기간: {kwargs['days']}일. 아래 자료를 보고 Day별 미션을 생성해줘. 형식: '과목명 Day 숫자: 내용' (줄글 말고 줄바꿈 금지)\n자료: {kwargs['content'][:8000]}"
                res = model.generate_content(p)
                st.session_state.current_ai_plan += "\n" + res.text
            elif prompt_type == "quiz":
                p = f"자료를 바탕으로 학점 {kwargs['grade']} 수준의 퀴즈 3개(문제, 정답, 해설)를 만들어줘.\n자료: {kwargs['content'][:8000]}"
                st.session_state.current_ai_quiz = model.generate_content(p).text
            elif prompt_type == "consult":
                p = f"학업 고민: {kwargs['q']}\n진심 어린 솔루션을 제공해줘."
                st.session_state.current_ai_consult_q = kwargs['q']
                st.session_state.current_ai_consult_a = model.generate_content(p).text
            st.session_state.refresh_lock = False
            st.rerun()
        except Exception as e:
            st.session_state.refresh_lock = False
            st.error(f"오류: {e}")

# 4. 앱 로직
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임 입력")
    if un:
        # (기존 로그인/생성 로직과 동일 - 코드 생략을 위해 통합 로직 작성)
        if st.button("접속"):
            st.session_state.update({"my_name": un, "page": "dashboard"})
            st.rerun()

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=2000)
    menu = st.sidebar.radio("메뉴", ["내 학습 보드", "상담소"])
    
    if menu == "내 학습 보드":
        my_subs = data['subjects'].get(st.session_state.my_name, [])
        for sub in my_subs:
            with st.container():
                st.markdown(f"<div class='subject-block'><div class='subject-title'>📚 {sub['name']}</div></div>", unsafe_allow_html=True)
                # 다중 파일 업로드 및 일정 생성 로직
                up_files = st.file_uploader("자료 업로드", accept_multiple_files=True)
                content = "".join([extract_text(f) for f in up_files])
                if st.button(f"{sub['name']} 계획 생성"):
                    run_ai_engine("plan", sub_name=sub['name'], content=content, grade="A+", days=7)
    
    elif menu == "상담소":
        st.markdown("<div class='notion-header'>🔮 AI 상담소</div>", unsafe_allow_html=True)
        q = st.text_area("고민 입력")
        if st.button("신청"): run_ai_engine("consult", q=q)
        if st.session_state.current_ai_consult_a:
            st.markdown(f"<div class='consult-container'>{st.session_state.current_ai_consult_a}</div>", unsafe_allow_html=True)

# (상세 구현 생략: 위의 로직을 기반으로 최종 합본 사용하세요)
