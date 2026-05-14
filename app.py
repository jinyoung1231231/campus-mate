import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 서비스 연결 초기화 ---
def init_connection():
    try:
        # 1. Secrets 로드 확인
        if "SUPABASE_URL" not in st.secrets:
            st.error("Secrets 설정에서 SUPABASE_URL을 찾을 수 없습니다.")
            st.stop()
            
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        
        # 2. Supabase 연결
        s = create_client(s_url, s_key)
        
        # 3. Gemini API 설정
        genai.configure(api_key=g_key)
        
        # 4. 모델 호출 (가장 최신 표준 명칭 사용)
        # 404 에러를 방지하기 위해 'models/' 접두사를 제거한 이름부터 시도합니다.
        m = None
        test_models = ['gemini-1.5-flash', 'gemini-1.5-pro']
        
        for model_id in test_models:
            try:
                temp_model = genai.GenerativeModel(model_id)
                # 실제로 작동하는지 최소 토큰으로 테스트
                temp_model.generate_content("ping", generation_config={"max_output_tokens": 1})
                m = temp_model
                break
            except Exception as e:
                continue
        
        return s, m
    except Exception as e:
        st.error(f"⚠️ 시스템 초기화 중 오류 발생: {e}")
        return None, None

# 연결 실행
supabase, model = init_connection()

# 연결 실패 시 안내 메시지 (상담 버튼 클릭 전 미리 경고)
if model is None:
    st.warning("⚠️ 현재 AI 모델과 연결되지 않았습니다. API 키가 정확한지, 혹은 구글 AI 스튜디오에서 키가 활성 상태(Active)인지 확인해 주세요.")

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
        career_q = st.text_area("고민 내용을 적어주세요 (예: 비전공자 개발자 취업 고민)")
        
        if st.button("🔮 상담 시작", use_container_width=True):
            if career_q:
                if model:
                    with st.spinner("AI 상담사가 분석 중입니다..."):
                        try:
                            # 1.5-flash 모델로 상담 실행
                            resp = model.generate_content(f"커리어 전문가로서 조언해줘: {career_q}")
                            st.session_state.career_result = resp.text
                            st.rerun()
                        except Exception as e:
                            st.error(f"상담 중 오류가 발생했습니다: {e}")
                else:
                    st.error("AI 모델이 연결되지 않아 상담을 진행할 수 없습니다. 상단의 경고 메시지를 확인하세요.")
            else:
                st.warning("고민 내용을 입력해 주세요.")

        if st.session_state.career_result:
            st.success("🤖 AI 상담사 결과")
            st.markdown(st.session_state.career_result)
            if st.button("결과 닫기"):
                st.session_state.career_result = None; st.rerun()
