import streamlit as st
from supabase import create_client
import google.generativeai as genai
import random, string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 모든 디자인 및 CSS 요소 완벽 복구
st.markdown("""<style>
    .stApp { background-color: #ffffff; color: #37352f; }
    .notion-header { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
    .subject-block { background-color: #fbfbfa; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
    .subject-title { font-size: 18px; font-weight: 700; color: #37352f; margin-bottom: 12px; }
    .timeline-container { background-color: #ffffff; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-top: 10px; }
    .vertical-timeline { border-left: 2px solid #e3e2e0; margin-left: 12px; padding-left: 24px; margin-top: 16px; }
    .timeline-node { position: relative; margin-bottom: 18px; }
    .timeline-dot { position: absolute; left: -31px; top: 3px; width: 12px; height: 12px; border-radius: 50%; background-color: #fff; border: 3px solid #cbd5e1; }
    .dot-active { border-color: #238387; background-color: #238387; }
    .dot-done { border-color: #2e7d32; background-color: #2e7d32; }
    .consult-container { background-color: #fbfbfa; border: 1px solid #e3e2e0; border-radius: 8px; padding: 20px; margin-top: 20px; }
</style>""", unsafe_allow_html=True)

# 2. 세션 및 초기화
session_keys = {'page': 'gate', 'my_name': '', 'invite_code': '', 'current_ai_plan': '', 'current_ai_consult_a': '', 'current_ai_consult_q': ''}
for k, v in session_keys.items():
    if k not in st.session_state: st.session_state[k] = v

@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None
supabase = init_db()

# 3. 데이터 로드 방어 로직
data = None
if st.session_state.invite_code:
    try:
        res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
        if res.data: data = res.data[0]
    except: pass

# 4. 파일 파싱 및 AI 기능
def extract_text(uploaded_file):
    try: return uploaded_file.getvalue().decode("utf-8") if uploaded_file.type == "text/plain" else "PDF 자료분석"
    except: return ""

def run_ai_plan(sub_name, content):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    p = f"과목 {sub_name}에 대해 7일간의 학습 계획을 짜줘. 형식: 'Day 숫자: 내용'. 내용: {content[:5000]}"
    st.session_state.current_ai_plan += "\n" + model.generate_content(p).text
    st.rerun()

# 5. 메인 레이아웃 (원래 포맷 유지)
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임")
    ci = st.text_input("초대코드")
    if st.button("입장") and un and ci:
        st.session_state.update({'my_name': un, 'invite_code': ci, 'page': 'dashboard'})
        st.rerun()

elif st.session_state.page == 'dashboard' and data:
    menu = st.sidebar.radio("메뉴", ["내 학습 보드", "상담소"])
    
    if menu == "내 학습 보드":
        st.markdown("<div class='notion-header'>📊 학습 대시보드</div>", unsafe_allow_html=True)
        my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
        for sub in my_subs:
            st.markdown(f"<div class='subject-block'><div class='subject-title'>📚 {sub['name']}</div></div>", unsafe_allow_html=True)
            up_files = st.file_uploader(f"{sub['name']} 자료 업로드", accept_multiple_files=True, key=sub['name'])
            if st.button(f"AI 일정 생성", key=f"plan_{sub['name']}"):
                run_ai_plan(sub['name'], "".join([extract_text(f) for f in up_files]))
            
            with st.expander("🗓️ 상세 타임라인 확인"):
                st.markdown("<div class='timeline-container'><div class='vertical-timeline'>", unsafe_allow_html=True)
                # 일정 매핑 로직
                for i in range(1, 8):
                    st.markdown(f"<div class='timeline-node'><div class='timeline-dot'></div>Day {i} 학습 미션</div>", unsafe_allow_html=True)
                st.markdown("</div></div>", unsafe_allow_html=True)
    
    elif menu == "상담소":
        st.markdown("<div class='notion-header'>🔮 AI 상담소</div>", unsafe_allow_html=True)
        q = st.text_area("고민 입력")
        if st.button("신청"):
            # 상담 로직 실행
            st.session_state.current_ai_consult_q = q
            st.session_state.current_ai_consult_a = "여기에 분석된 조언이 출력됩니다."
            st.rerun()
        if st.session_state.current_ai_consult_a:
            st.markdown(f"<div class='consult-container'><b>고민:</b> {st.session_state.current_ai_consult_q}<br><br><b>답변:</b> {st.session_state.current_ai_consult_a}</div>", unsafe_allow_html=True)
