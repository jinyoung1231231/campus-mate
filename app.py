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

# --- 2. 세션 상태 초기화 (매우 중요) ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_teams' not in st.session_state:
    st.session_state.my_teams = {} # {코드: 팀이름}
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""

# --- 3. 핵심 로직 함수 ---
def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except:
        return None

def update_db_status(code, name, status):
    data = get_team_data(code)
    if data:
        m_list = data['members']
        for m in m_list:
            if m['name'] == name:
                m['status'] = status
        supabase.table("team").update({"members": m_list}).eq("invite_code", code).execute()

def update_db_subjects(code, name, subs):
    data = get_team_data(code)
    if data:
        all_subs = data.get('subjects', {})
        all_subs[name] = subs
        supabase.table("team").update({"subjects": all_subs}).eq("invite_code", code).execute()

# --- 4. 화면 로직 ---

# [화면 0: 게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.subheader("AI 실시간 멀티 스터디 플랫폼")
    
    if st.session_state.my_teams:
        st.write("### 🏠 나의 참여 팀")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} (코드: {code})", key=f"go_{code}", use_container_width=True):
                    st.session_state.invite_code = code
                    st.session_state.page = 'dashboard'
                    st.rerun()
            with col_b:
                if st.button("❌", key=f"out_{code}"):
                    del st.session_state.my_teams[code]
                    st.rerun()
        st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True):
            st.session_state.page = 'create'
            st.rerun()
    with c2:
        if st.button("🔗 팀 참여", use_container_width=True):
            st.session_state.page = 'join'
            st.rerun()

# [화면 1: 팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 새로운 팀 만들기")
    t_name = st.text_input("팀 이름", placeholder="예: 파이썬 열공방")
    u_name = st.text_input("사용할 닉네임", placeholder="예: 홍길동")
    
    if st.button("팀 만들기 및 입장"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            try:
                # DB 저장
                supabase.table("team").insert({
                    "invite_code": code,
                    "team_name": t_name,
                    "members": [{"name": u_name, "status": "✅ 대기 중"}],
                    "subjects": {u_name: ["자유 공부"]}
                }).execute()
                
                # 세션에 정보 고정 (중요!)
                st.session_state.my_teams[code] = t_name
                st.session_state.invite_code = code
                st.session_state.my_name = u_name
                st.session_state.page = 'dashboard'
                st.rerun()
            except Exception as e:
                st.error(f"생성 실패: {e}")
        else:
            st.warning("모든 정보를 입력해주세요.")

# [화면 2: 팀 참여]
elif st.session_state.page == 'join':
    st.title("🔗 기존 팀 참여")
    code_in = st.text_input("초대 코드 6자리").upper()
    u_name = st.text_input("사용할 닉네임")
    
    if st.button("팀 참여 및 입장"):
        data = get_team_data(code_in)
        if data:
            m_list = data['members']
            all_subs = data.get('subjects', {})
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기 중"})
                if u_name not in all_subs:
                    all_subs[u_name] = ["자유 공부"]
                supabase.table("team").update({"members": m_list, "subjects": all_subs}).eq("invite_code", code_in).execute()
            
            st.session_state.my_teams[code_in] = data['team_name']
            st.session_state.invite_code = code_in
            st.session_state.my_name = u_name
            st.session_state.page = 'dashboard'
            st.rerun()
        else:
            st.error("해당 코드를 가진 팀이 없습니다.")

# [화면 3: 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=5000, key="f5") # 5초 자동 갱신
    
    data = get_team_data(st.session_state.invite_code)
    if not data:
        st.error("데이터 로딩 실패")
        if st.button("홈으로"):
            st.session_state.page = 'gate'
            st.rerun()
        st.stop()
        
    st.title(f"🏫 {data['team_name']}")
    st.sidebar.title("⚙️ 메뉴")
    if st.sidebar.button("⬅️ 다른 팀 선택"):
        st.session_state.page = 'gate'
        st.rerun()

    # 1. 팀원 실시간 현황
    st.subheader("👥 팀원 실시간 상태")
    cols = st.columns(5)
    for i, m in enumerate(data['members']):
        with cols[i % 5]:
            status_color = "green" if "🔥" in m['status'] else "gray"
            st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:10px; padding:10px; text-align:center; background-color:white;">
                    <b style="color:black;">{m['name']}</b><br>
                    <span style="color:{status_color}; font-size:0.8em;">{m['status']}</span>
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 2. 개인별 과목 및 학습
    my_name = st.session_state.my_name
    my_subs = data.get('subjects', {}).get(my_name, ["자유 공부"])
    
    st.subheader(f"📚 {my_name}님의 학습실")
    
    c_add1, c_add2 = st.columns([3, 1])
    with c_add1:
        new_s = st.text_input("새 과목 추가", placeholder="예: 경제학, 알고리즘", label_visibility="collapsed")
    with c_add2:
        if st.button("➕ 추가", use_container_width=True):
            if new_s and new_s not in my_subs:
                my_subs.append(new_s)
                update_db_subjects(st.session_state.invite_code, my_name, my_subs)
                st.rerun()

    tabs = st.tabs(my_subs)
    for i, tab in enumerate(tabs):
        s_name = my_subs[i]
        with tab:
            col_t, col_d = st.columns([4, 1])
            with col_t: st.write(f"📖 **{s_name}** 학습 진행")
            with col_d:
                if st.button("❌", key=f"del_{s_name}"):
                    my_subs.remove(s_name)
                    update_db_subjects(st.session_state.invite_code, my_name, my_subs)
                    st.rerun()

            up_file = st.file_uploader(f"자료 업로드", key=f"f_{s_name}")
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button(f"🚀 {s_name} 시작", key=f"st_{s_name}", use_container_width=True):
                    update_db_status(st.session_state.invite_code, my_name, f"🔥 {s_name} 중")
                    st.rerun()
            with cb2:
                if st.button(f"🏁 {s_name} 종료/퀴즈", key=f"ed_{s_name}", use_container_width=True):
                    update_db_status(st.session_state.invite_code, my_name, "✅ 대기 중")
                    if up_file:
                        with st.spinner("AI 퀴즈 생성 중..."):
                            resp = model.generate_content(f"{s_name} 핵심 퀴즈 3개 내줘.")
                            st.session_state.last_quiz = resp.text
                            st.rerun()

    if 'last_quiz' in st.session_state:
        with st.expander("🤖 AI 학습 퀴즈", expanded=True):
            st.write(st.session_state.last_quiz)
            if st.button("확인 완료"):
                del st.session_state.last_quiz
                st.rerun()

    st.divider()
    st.subheader("💡 AI 진로 상담소")
    career_q = st.text_area("고민을 적어주세요")
    if st.button("🔮 컨설팅 받기"):
        if career_q:
            resp = model.generate_content(f"커리어 상담가로서 조언해줘: {career_q}")
            st.info(resp.text)
