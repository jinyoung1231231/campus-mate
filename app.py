import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 보안 설정 및 연결 (진단 모드) ---
def init_connection():
    try:
        # 1. Secrets 존재 확인
        if "SUPABASE_URL" not in st.secrets:
            st.error("❌ Secrets에 'SUPABASE_URL'이 없습니다.")
            st.stop()
        
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        
        # 2. Supabase 연결
        s = create_client(s_url, s_key)
        
        # 3. Gemini 연결 시도
        genai.configure(api_key=g_key)
        
        # 가장 표준적인 모델 하나만 집중 타격
        m = genai.GenerativeModel('gemini-1.5-flash')
        
        # [중요] 실제로 키가 작동하는지 짧은 테스트
        m.generate_content("hi", generation_config={"max_output_tokens": 1})
        
        return s, m
    except Exception as e:
        # 실패 시 에러의 정체를 화면에 박제합니다.
        st.error(f"🚨 연결 실패 원인: {e}")
        return None, None

# 캐시를 사용하지 않고 우선 연결 시도 (에러 확인을 위해)
supabase, model = init_connection()

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_teams' not in st.session_state:
    st.session_state.my_teams = {}
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""
if 'career_result' not in st.session_state:
    st.session_state.career_result = None

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

# --- 3. 화면 UI 로직 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 나의 팀 리스트")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} [코드: {code}]", key=f"go_{code}", use_container_width=True):
                    st.session_state.invite_code = code
                    st.session_state.page = 'dashboard'; st.rerun()
            with col_b:
                if st.button("❌", key=f"out_{code}"):
                    del st.session_state.my_teams[code]; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True): st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여", use_container_width=True): st.session_state.page = 'join'; st.rerun()

elif st.session_state.page == 'create':
    st.title("🆕 새로운 팀 만들기")
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

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.error(f"📢 초대 코드: **{st.session_state.invite_code}**")
        
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["자유 공부"])
        
        st.subheader(f"📚 {my_name}님의 학습실")
        # 과목 시작/종료 버튼
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("🔥 공부 시작", use_container_width=True):
                update_db_status(st.session_state.invite_code, my_name, "🔥 열공 중"); st.rerun()
        with cb2:
            if st.button("✅ 휴식/종료", use_container_width=True):
                update_db_status(st.session_state.invite_code, my_name, "✅ 대기 중"); st.rerun()

        st.divider()
        
        # --- AI 상담소 영역 ---
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("진로 고민을 적어주세요", key="career_input")
        
        if st.button("🔮 상담 시작", use_container_width=True):
            if career_q:
                if model:
                    with st.spinner("AI 상담사가 분석 중입니다..."):
                        try:
                            resp = model.generate_content(f"조언해줘: {career_q}")
                            st.session_state.career_result = resp.text
                            st.rerun()
                        except Exception as e:
                            st.error(f"상담 실행 에러: {e}")
                else:
                    st.error("🚨 AI 모델이 연결되지 않았습니다. 상단의 에러 메시지를 확인하세요.")
            else:
                st.warning("내용을 입력해주세요.")

        if st.session_state.career_result:
            st.success("🤖 AI 상담 결과")
            st.markdown(st.session_state.career_result)
            if st.button("결과 닫기"):
                st.session_state.career_result = None; st.rerun()
