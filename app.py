import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 설정 (본인의 키로 교체하세요) ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co" 
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyAvwGS0XZ9zGkRnbAmvUFmD6tgff0nCrFs"

@st.cache_resource
def init_connection():
    # Supabase 연결
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Gemini 설정
    genai.configure(api_key=GEMINI_API_KEY)
    
    # [수정 포인트] NotFound(404) 에러를 피하기 위한 모델 선택 로직
    # v1beta나 특정 환경에서 가장 잘 작동하는 이름을 순차적으로 시도합니다.
    model_names = ['gemini-1.5-flash', 'gemini-pro', 'models/gemini-1.5-flash']
    
    m = None
    for name in model_names:
        try:
            temp_model = genai.GenerativeModel(name)
            # 모델이 유효한지 확인하기 위해 아주 짧은 텍스트 생성 테스트
            temp_model.generate_content("Hi", generation_config={"max_output_tokens": 1})
            m = temp_model
            break # 성공하면 루프 탈출
        except Exception:
            continue
            
    if m is None:
        st.error("사용 가능한 Gemini 모델을 찾을 수 없습니다. API 키나 권한을 확인해주세요.")
        
    return s, m

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"연결 오류 발생: {e}")

# --- 이하 세션 상태 및 화면 로직은 이전과 동일 (전체 코드 유지) ---
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
    except: return None

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

# [화면 로직 시작]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 팀")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                    st.session_state.invite_code = code
                    st.session_state.page = 'dashboard'; st.rerun()
            with col_b:
                if st.button("❌", key=f"out_{code}"):
                    del st.session_state.my_teams[code]; st.rerun()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True): st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여", use_container_width=True): st.session_state.page = 'join'; st.rerun()

elif st.session_state.page == 'create':
    st.title("🆕 팀 만들기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("완료"):
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

elif st.session_state.page == 'join':
    st.title("🔗 팀 참여")
    code_in = st.text_input("코드 입력").upper()
    u_name = st.text_input("닉네임")
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

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=5000, key="f5")
    data = get_team_data(st.session_state.invite_code)
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.sidebar.button("⬅️ 목록으로", on_click=lambda: st.session_state.update({"page": "gate"}))
        st.subheader("👥 팀원 현황")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                st.info(f"**{m['name']}**\n\n{m['status']}")
        st.divider()
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["자유 공부"])
        st.subheader(f"📚 {my_name}님의 학습")
        new_s = st.text_input("과목 추가", label_visibility="collapsed")
        if st.button("➕ 추가"):
            if new_s and new_s not in my_subs:
                my_subs.append(new_s); update_db_subjects(st.session_state.invite_code, my_name, my_subs); st.rerun()
        if my_subs:
            tabs = st.tabs(my_subs)
            for i, tab in enumerate(tabs):
                s_name = my_subs[i]
                with tab:
                    if st.button(f"❌ {s_name} 삭제", key=f"del_{s_name}"):
                        my_subs.remove(s_name); update_db_subjects(st.session_state.invite_code, my_name, my_subs); st.rerun()
                    up_file = st.file_uploader(f"자료 업로드", key=f"f_{s_name}")
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button(f"🚀 시작", key=f"st_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, f"🔥 {s_name} 중"); st.rerun()
                    with cb2:
                        if st.button(f"🏁 종료/퀴즈", key=f"ed_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, "✅ 대기"); st.rerun()
                            if up_file:
                                with st.spinner("AI 퀴즈 생성 중..."):
                                    try:
                                        resp = model.generate_content(f"{s_name}에 대한 퀴즈 3개 내줘.")
                                        st.session_state.last_quiz = resp.text
                                        st.rerun()
                                    except Exception as e: st.error(f"퀴즈 생성 에러: {e}")
        if 'last_quiz' in st.session_state:
            with st.expander("🤖 AI 학습 퀴즈 결과", expanded=True):
                st.write(st.session_state.last_quiz)
                if st.button("확인 완료"): del st.session_state.last_quiz; st.rerun()
        st.divider()
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("진로 고민을 적어주세요")
        if st.button("🔮 상담 시작"):
            if career_q:
                with st.spinner("분석 중..."):
                    try:
                        resp = model.generate_content(f"커리어 상담가로서 조언해줘: {career_q}")
                        st.info(resp.text)
                    except Exception as e: st.error(f"상담 에러: {e}")
