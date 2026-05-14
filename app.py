import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 설정 (본인의 키로 교체) ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co" 
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

@st.cache_resource
def init_connection():
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    m = genai.GenerativeModel('gemini-1.5-flash')
    return s, m

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"연결 오류: {e}")

# --- 2. 로컬 팀 리스트 관리 (세션 기반 유지) ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_teams' not in st.session_state:
    # { "초대코드": "팀이름" } 형태로 저장
    st.session_state.my_teams = {}

# --- 3. DB 함수 ---
def get_team_data(code):
    res = supabase.table("team").select("*").eq("invite_code", code).execute()
    return res.data[0] if res.data else None

def update_db_status(code, name, status):
    data = get_team_data(code)
    if data:
        m_list = data['members']
        for m in m_list:
            if m['name'] == name: m['status'] = status
        supabase.table("team").update({"members": m_list}).eq("invite_code", code).execute()

def update_db_subjects(code, name, subs):
    data = get_team_data(code)
    if data:
        all_subs = data.get('subjects', {})
        all_subs[name] = subs
        supabase.table("team").update({"subjects": all_subs}).eq("invite_code", code).execute()

# --- 4. 화면 로직 ---

# [화면 0: 게이트웨이 - 팀 리스트 제공]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    
    # 내가 참여 중인 팀 리스트 표시
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 팀")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                    st.session_state.update({"invite_code": code, "page": "dashboard"})
                    st.rerun()
            with col_b:
                if st.button("❌", key=f"out_{code}"):
                    del st.session_state.my_teams[code]
                    st.rerun()
        st.divider()

    st.subheader("➕ 새로운 시작")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True):
            st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여", use_container_width=True):
            st.session_state.page = 'join'; st.rerun()

# [화면 1: 팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 팀 만들기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("생성 완료"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": t_name,
                "members": [{"name": u_name, "status": "✅ 대기"}],
                "subjects": {u_name: ["기본 과목"]}
            }).execute()
            # 팀 목록에 추가
            st.session_state.my_teams[code] = t_name
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [화면 2: 참여하기]
elif st.session_state.page == 'join':
    st.title("🔗 팀 참여")
    code_in = st.text_input("코드 입력").upper()
    u_name = st.text_input("닉네임")
    if st.button("입장"):
        data = get_team_data(code_in)
        if data:
            m_list = data['members']
            subs = data.get('subjects', {})
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기"})
                if u_name not in subs: subs[u_name] = ["기본 과목"]
                supabase.table("team").update({"members": m_list, "subjects": subs}).eq("invite_code", code_in).execute()
            
            # 팀 목록에 추가
            st.session_state.my_teams[code_in] = data['team_name']
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()
        else:
            st.error("팀을 찾을 수 없습니다.")

# [화면 3: 대시보드 - 기존과 동일]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=5000, key="f5")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.subheader(f"👥 팀원 현황 ({st.session_state.invite_code})")
        # (기존 대시보드 로직 동일...)
        
        # 상단에 '다른 팀으로 가기' 버튼 추가
        if st.sidebar.button("⬅️ 팀 목록으로"):
            st.session_state.page = 'gate'
            st.rerun()
        
        # (이하 과목 관리, AI 퀴즈 등 기존 코드 유지)
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["기본 과목"])
        
        st.write(f"반갑습니다, **{my_name}**님!")
        # ... (중략: 기존 과목 탭 및 학습 로직) ...
