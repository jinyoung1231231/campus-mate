import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 보안 설정 (Streamlit Secrets 사용) ---
# 대시보드 Settings > Secrets에 아래 3개 키가 입력되어 있어야 합니다.
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Streamlit Secrets 설정이 필요합니다. (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY)")
    st.stop()

@st.cache_resource
def init_connection():
    # Supabase 연결
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Gemini 설정
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 모델 연결 (가장 안정적인 모델명 사용)
    m = None
    for model_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            temp_model = genai.GenerativeModel(model_name)
            # 연결 확인용 테스트
            temp_model.generate_content("hi", generation_config={"max_output_tokens": 1})
            m = temp_model
            break
        except:
            continue
    return s, m

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"초기 연결 실패: {e}")

# --- 2. 데이터 관리 함수 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_teams' not in st.session_state:
    st.session_state.my_teams = {}
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""

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
            if m['name'] == name: m['status'] = status
        supabase.table("team").update({"members": m_list}).eq("invite_code", code).execute()

def update_db_subjects(code, name, subs):
    data = get_team_data(code)
    if data:
        all_subs = data.get('subjects', {})
        all_subs[name] = subs
        supabase.table("team").update({"subjects": all_subs}).eq("invite_code", code).execute()

# --- 3. 화면 UI 로직 ---

# [화면: 게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.caption("AI 실시간 멀티 스터디 & 진로 플랫폼")
    
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 팀")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
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
            st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여", use_container_width=True):
            st.session_state.page = 'join'; st.rerun()

# [화면: 팀 생성]
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
                "subjects": {u_name: ["자유 공부"]}
            }).execute()
            st.session_state.my_teams[code] = t_name
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [화면: 팀 참여]
elif st.session_state.page == 'join':
    st.title("🔗 팀 참여")
    code_in = st.text_input("코드 6자리").upper()
    u_name = st.text_input("내 닉네임")
    if st.button("입장"):
        data = get_team_data(code_in)
        if data:
            m_list = data['members']
            all_subs = data.get('subjects', {})
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기"})
                if u_name not in all_subs: all_subs[u_name] = ["자유 공부"]
                supabase.table("team").update({"members": m_list, "subjects": all_subs}).eq("invite_code", code_in).execute()
            st.session_state.my_teams[code_in] = data['team_name']
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [화면: 메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=5000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.sidebar.button("⬅️ 목록으로", on_click=lambda: st.session_state.update({"page": "gate"}))
        
        # 1. 팀원 현황
        st.subheader("👥 팀원 현황")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                st.info(f"**{m['name']}**\n\n{m['status']}")
        
        st.divider()
        
        # 2. 내 과목 관리 (데이터 유지)
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["자유 공부"])
        
        st.subheader(f"📚 {my_name}님의 학습실")
        new_s = st.text_input("과목 추가", label_visibility="collapsed", placeholder="새 과목 입력")
        if st.button("➕ 추가"):
            if new_s and new_s not in my_subs:
                my_subs.append(new_s)
                update_db_subjects(st.session_state.invite_code, my_name, my_subs)
                st.rerun()
        
        if my_subs:
            tabs = st.tabs(my_subs)
            for i, tab in enumerate(tabs):
                s_name = my_subs[i]
                with tab:
                    col_t, col_d = st.columns([4, 1])
                    with col_t: st.write(f"📖 **{s_name}**")
                    with col_d:
                        if st.button("❌", key=f"del_{s_name}"):
                            my_subs.remove(s_name)
                            update_db_subjects(st.session_state.invite_code, my_name, my_subs)
                            st.rerun()
                    
                    up_file = st.file_uploader(f"자료 업로드", key=f"f_{s_name}")
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button(f"🚀 시작", key=f"st_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, f"🔥 {s_name} 중")
                            st.rerun()
                    with cb2:
                        if st.button(f"🏁 퀴즈", key=f"ed_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, "✅ 대기")
                            if up_file and model:
                                with st.spinner("AI 퀴즈 생성 중..."):
                                    resp = model.generate_content(f"{s_name}에 대한 퀴즈 3개 내줘.")
                                    st.session_state.last_quiz = resp.text
                                    st.rerun()
        
        if 'last_quiz' in st.session_state:
            with st.expander("🤖 AI 학습 퀴즈 결과", expanded=True):
                st.write(st.session_state.last_quiz)
                if st.button("확인 완료"):
                    del st.session_state.last_quiz; st.rerun()

        st.divider()
        # 3. AI 진로 상담소
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("진로 고민을 적어주세요")
        if st.button("🔮 상담 시작", use_container_width=True):
            if career_q and model:
                with st.spinner("분석 중..."):
                    resp = model.generate_content(f"커리어 상담가로서 조언해줘: {career_q}")
                    st.info(resp.text)
