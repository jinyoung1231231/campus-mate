import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh # requirements.txt에 추가 필수!

# --- 1. 설정 ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co"
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

@st.cache_resource
def init_connection():
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    m = genai.GenerativeModel('gemini-1.5-flash')
    return s, m

supabase, model = init_connection()

if 'page' not in st.session_state:
    st.session_state.page = 'gate'

def update_db_status(new_status):
    res = supabase.table("team").select("members").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        m_list = res.data[0]['members']
        for m in m_list:
            if m['name'] == st.session_state.my_name:
                m['status'] = new_status
        supabase.table("team").update({"members": m_list}).eq("invite_code", st.session_state.invite_code).execute()

# --- 2. 화면 로직 ---

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성"):
            st.session_state.page = 'create'
            st.rerun()
    with c2:
        if st.button("🔗 참여하기"):
            st.session_state.page = 'join'
            st.rerun()

# [팀 생성]
elif st.session_state.page == 'create':
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("만들기"):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        supabase.table("team").insert({
            "invite_code": code, "team_name": t_name,
            "members": [{"name": u_name, "status": "✅ 대기"}],
            "subjects": {"기본": {}}
        }).execute()
        st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
        st.rerun()

# [참여하기]
elif st.session_state.page == 'join':
    code_in = st.text_input("코드 입력").upper()
    u_name = st.text_input("내 닉네임")
    if st.button("입장"):
        res = supabase.table("team").select("*").eq("invite_code", code_in).execute()
        if res.data:
            m_list = res.data[0]['members']
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기"})
                supabase.table("team").update({"members": m_list}).eq("invite_code", code_in).execute()
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [대시보드] - 여기서 SyntaxError가 났던 부분입니다!
elif st.session_state.page == 'dashboard':
    # 5초 자동 새로고침 (팀원 입장 실시간 확인용)
    st_autorefresh(interval=5000, key="f5")
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        data = res.data[0]
        st.title(f"🏫 {data['team_name']}")
        
        # 팀원 현황
        st.subheader("👥 팀원 현황")
        cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with cols[i%5]:
                st.info(f"{m['name']}\n\n{m['status']}")
        
        st.divider()
        # 과목/AI 퀴즈 생략 (테스트를 위해 기본 구조만 유지)
        if st.button("로그아웃"):
            st.session_state.page = 'gate'
            st.rerun()
