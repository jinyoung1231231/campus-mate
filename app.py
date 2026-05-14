import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 서비스 연결 초기화 (에러 진단 모드) ---
def init_connection():
    try:
        # Secrets 로드
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        
        # Supabase 연결
        s = create_client(s_url, s_key)
        
        # Gemini API 설정
        genai.configure(api_key=g_key)
        
        # [해결 핵심] 모델 목록을 직접 조회하여 사용 가능한 첫 번째 모델을 잡습니다.
        m = None
        try:
            # 사용 가능한 모델 목록 중 generateContent가 가능한 모델 찾기
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 우선순위: 1.5-flash -> 1.5-pro -> 목록의 첫 번째
            target_model = ""
            if "models/gemini-1.5-flash" in available_models:
                target_model = "models/gemini-1.5-flash"
            elif "models/gemini-1.0-pro" in available_models:
                target_model = "models/gemini-1.0-pro"
            elif available_models:
                target_model = available_models[0]
                
            if target_model:
                m = genai.GenerativeModel(target_model)
                # 연결 테스트
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
        except Exception as inner_e:
            st.error(f"모델 목록 조회 중 에러: {inner_e}")
            # 리스트 조회가 실패할 경우를 대비한 수동 시도
            try:
                m = genai.GenerativeModel('gemini-1.5-flash')
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
            except:
                m = None
        
        return s, m
    except Exception as e:
        st.error(f"⚠️ 시스템 초기화 중 치명적 오류: {e}")
        return None, None

# 연결 실행
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

# --- 3. 화면 UI 로직 ---

# 상단 연결 상태 표시 (디버깅용)
if model is None:
    st.error("🚨 AI 모델 연결 실패. API 키 권한이나 라이브러리 버전을 확인하세요.")
else:
    st.sidebar.success("✅ AI 모델 연결 완료")

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 참여 중인 팀")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
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

# [팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 팀 만들기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("사용할 닉네임")
    if st.button("생성 완료"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": t_name,
                "members": [{"name": u_name, "status": "✅ 대기 중"}],
                "subjects": {u_name: ["기본 공부"]}
            }).execute()
            st.session_state.my_teams[code] = t_name
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=15000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.error(f"📢 초대 코드: {st.session_state.invite_code}")
        st.sidebar.button("⬅️ 목록으로", on_click=lambda: st.session_state.update({"page": "gate"}))
        
        st.subheader("👥 실시간 현황")
        cols = st.columns(4)
        for i, m in enumerate(data['members']):
            with cols[i % 4]:
                st.info(f"**{m['name']}**\n{m['status']}")
        
        st.divider()
        my_name = st.session_state.my_name
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 공부 시작", use_container_width=True):
                update_db_status(st.session_state.invite_code, my_name, "🔥 열공 중"); st.rerun()
        with c2:
            if st.button("✅ 휴식하기", use_container_width=True):
                update_db_status(st.session_state.invite_code, my_name, "✅ 대기 중"); st.rerun()

        st.divider()
        # AI 상담소
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("고민 내용을 적어주세요")
        
        if st.button("🔮 상담 시작", use_container_width=True):
            if career_q:
                if model:
                    with st.spinner("AI 상담사가 분석 중입니다..."):
                        try:
                            resp = model.generate_content(f"커리어 전문가로서 조언해줘: {career_q}")
                            st.session_state.career_result = resp.text
                            st.rerun()
                        except Exception as e:
                            st.error(f"상담 실행 중 에러: {e}")
                else:
                    st.error("AI 연결이 되어 있지 않습니다.")
            else:
                st.warning("고민 내용을 입력해 주세요.")

        if st.session_state.career_result:
            st.success("🤖 AI 상담 결과")
            st.markdown(st.session_state.career_result)
            if st.button("결과 닫기"):
                st.session_state.career_result = None; st.rerun()
