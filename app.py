import streamlit as st
from supabase import create_client
import google.generativeai as genai
import random, string
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. CSS & 초기화
st.markdown("""<style>
    .stApp { background-color: #ffffff; color: #37352f; }
    .subject-block { background-color: #fbfbfa; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
    .timeline-container { background-color: #ffffff; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-top: 10px; }
    .vertical-timeline { border-left: 2px solid #e3e2e0; margin-left: 12px; padding-left: 24px; }
    .timeline-node { margin-bottom: 18px; position: relative; }
    .timeline-dot { position: absolute; left: -31px; top: 3px; width: 12px; height: 12px; border-radius: 50%; background-color: #fff; border: 3px solid #cbd5e1; }
    .dot-active { border-color: #238387; background-color: #238387; }
</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_db(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_db()

# 세션 초기화
for key in ['page', 'my_name', 'invite_code', 'current_mode', 'active_subject', 'active_day', 'current_ai_plan']:
    if key not in st.session_state: st.session_state[key] = ''

# 2. 데이터 페칭 (NameError 방지: 모든 로직보다 상단에서 선언)
data = None
if st.session_state.invite_code:
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    if res.data: data = res.data[0]

# 3. 메인 앱 로직
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임 입력")
    if un and st.button("접속"):
        st.session_state.update({"my_name": un, "page": "dashboard"})
        st.rerun()

elif st.session_state.page == 'dashboard' and data:
    menu = st.sidebar.radio("메뉴", ["내 학습 보드", "상담소"])
    
    if menu == "내 학습 보드":
        my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
        for sub in my_subs:
            with st.container():
                st.markdown(f"<div class='subject-block'><div class='subject-title'>📚 {sub['name']}</div></div>", unsafe_allow_html=True)
                up_files = st.file_uploader(f"{sub['name']} 자료 업로드", accept_multiple_files=True, key=sub['name'])
                if st.button(f"{sub['name']} 계획 생성"):
                    content = "".join([extract_text(f) for f in up_files])
                    # AI 실행 로직 연결
                    st.session_state.current_ai_plan += f"\n{sub['name']} Day 1: {content[:100]}" 
                    st.rerun()
                
                # 타임라인 보드
                with st.expander("일정 확인"):
                    st.markdown("<div class='timeline-container'><div class='vertical-timeline'>", unsafe_allow_html=True)
                    for i in range(1, 8):
                        st.markdown(f"<div class='timeline-node'><div class='timeline-dot'></div>Day {i} 미션 수행</div>", unsafe_allow_html=True)
                    st.markdown("</div></div>", unsafe_allow_html=True)
                    
    elif menu == "상담소":
        st.subheader("🔮 AI 1:1 진로 상담")
        q = st.text_area("고민 입력")
        if st.button("신청"):
            # AI 상담 로직
            st.session_state.current_ai_consult_a = "여기에 AI 분석 답변이 아래로 출력됩니다."
        st.write(st.session_state.current_ai_consult_a)

def extract_text(uploaded_file):
    try:
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""
