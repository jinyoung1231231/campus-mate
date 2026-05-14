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

# --- 2. 상태 및 DB 관리 로직 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'

# DB에서 팀 정보를 가져오는 공통 함수
def get_team_data():
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    return res.data[0] if res.data else None

# 내 상태(공부 중 등) 업데이트
def update_db_status(new_status):
    data = get_team_data()
    if data:
        m_list = data['members']
        for m in m_list:
            if m['name'] == st.session_state.my_name:
                m['status'] = new_status
        supabase.table("team").update({"members": m_list}).eq("invite_code", st.session_state.invite_code).execute()

# 내 과목 리스트를 DB에 영구 저장/삭제
def update_db_subjects(new_subjects):
    data = get_team_data()
    if data:
        all_subjects = data.get('subjects', {})
        # 사용자의 이름을 키로 하여 과목 리스트 저장
        all_subjects[st.session_state.my_name] = new_subjects
        supabase.table("team").update({"subjects": all_subjects}).eq("invite_code", st.session_state.invite_code).execute()

# --- 3. 화면 로직 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True):
            st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 참여하기", use_container_width=True):
            st.session_state.page = 'join'; st.rerun()

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
                "subjects": {u_name: ["기본 과목"]} # 생성자 과목 초기화
            }).execute()
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

elif st.session_state.page == 'join':
    st.title("🔗 팀 참여")
    code_in = st.text_input("코드 입력").upper()
    u_name = st.text_input("닉네임")
    if st.button("입장"):
        res = supabase.table("team").select("*").eq("invite_code", code_in).execute()
        if res.data:
            data = res.data[0]
            m_list = data['members']
            subs = data.get('subjects', {})
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기"})
                if u_name not in subs: subs[u_name] = ["기본 과목"]
                supabase.table("team").update({"members": m_list, "subjects": subs}).eq("invite_code", code_in).execute()
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=5000, key="f5")
    data = get_team_data()
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        
        # 1. 팀원 현황
        st.subheader("👥 팀원 현황")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                st.markdown(f"<div style='border:1px solid #ddd; padding:5px; border-radius:5px; text-align:center;'><b>{m['name']}</b><br><small>{m['status']}</small></div>", unsafe_allow_html=True)

        st.divider()

        # 2. 내 과목 관리 (DB 기반)
        st.subheader("📚 나의 학습실")
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["기본 과목"])

        c_sub1, c_sub2 = st.columns([3, 1])
        with c_sub1:
            new_s = st.text_input("추가할 과목명", label_visibility="collapsed")
        with c_sub2:
            if st.button("➕ 추가", use_container_width=True):
                if new_s and new_s not in my_subs:
                    my_subs.append(new_s)
                    update_db_subjects(my_subs)
                    st.rerun()

        if my_subs:
            tabs = st.tabs(my_subs)
            for i, tab in enumerate(tabs):
                s_name = my_subs[i]
                with tab:
                    col_t1, col_t2 = st.columns([4, 1])
                    with col_t1: st.write(f"📖 **{s_name}** 학습")
                    with col_t2:
                        if st.button("❌", key=f"del_{s_name}"):
                            my_subs.remove(s_name)
                            update_db_subjects(my_subs)
                            st.rerun()
                    
                    up_file = st.file_uploader(f"{s_name} 자료", key=f"f_{s_name}")
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button(f"🚀 시작", key=f"s_{s_name}", use_container_width=True):
                            update_db_status(f"🔥 {s_name} 중"); st.rerun()
                    with cb2:
                        if st.button(f"🏁 퀴즈", key=f"e_{s_name}", use_container_width=True):
                            update_db_status("✅ 대기"); st.rerun()

        st.divider()
        # AI 상담소 생략 (기존 코드와 동일하게 추가 가능)
        if st.button("🚪 로그아웃"):
            st.session_state.page = 'gate'; st.rerun()
