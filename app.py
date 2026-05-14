import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 보안 설정 및 연결 (404 및 권한 이슈 해결 버전) ---
def init_connection():
    try:
        # Secrets 로드
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        
        # 1. Supabase 연결
        s = create_client(s_url, s_key)
        
        # 2. Gemini API 설정
        genai.configure(api_key=g_key)
        
        # 3. 모델 로드 시도 (가장 호환성이 높은 이름들)
        m = None
        for model_id in ['gemini-1.5-flash', 'gemini-pro', 'models/gemini-1.5-flash']:
            try:
                temp_model = genai.GenerativeModel(model_id)
                # 연결 테스트 (실제 호출이 가능한지 확인)
                temp_model.generate_content("hi", generation_config={"max_output_tokens": 1})
                m = temp_model
                break # 성공하면 루프 탈출
            except Exception as e:
                # 개별 모델 시도 실패 시 로그 (사용자에게는 숨김)
                continue
        
        if m is None:
            st.error("🚨 모든 Gemini 모델 호출에 실패했습니다. API 키의 활성화 상태를 확인하세요.")
            
        return s, m
    except Exception as e:
        st.error(f"🚨 시스템 초기화 에러: {e}")
        return None, None

# 앱 시작 시 연결 실행
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

# DB 보조 함수
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
        if st.button("🆕 팀 생성"): st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여"): st.session_state.page = 'join'; st.rerun()

# [팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 팀 생성")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("닉네임")
    if st.button("완료"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": t_name,
                "members": [{"name": u_name, "status": "✅ 대기"}],
                "subjects": {u_name: ["공부"]}
            }).execute()
            st.session_state.my_teams[code] = t_name
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [참여]
elif st.session_state.page == 'join':
    st.title("🔗 팀 참여")
    code_in = st.text_input("초대 코드").upper()
    u_name = st.text_input("닉네임")
    if st.button("입장"):
        data = get_team_data(code_in)
        if data:
            m_list = data['members']
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기"})
                supabase.table("team").update({"members": m_list}).eq("invite_code", code_in).execute()
            st.session_state.my_teams[code_in] = data['team_name']
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=20000, key="refresh") # 갱신 주기를 20초로 늘림
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.info(f"초대 코드: {st.session_state.invite_code}")
        st.sidebar.button("⬅️ 목록으로", on_click=lambda: st.session_state.update({"page": "gate"}))
        
        # 팀원 현황
        st.subheader("👥 실시간 현황")
        cols = st.columns(4)
        for i, m in enumerate(data['members']):
            with cols[i % 4]:
                st.info(f"**{m['name']}**\n{m['status']}")
        
        st.divider()
        # 공부 상태 변경
        my_name = st.session_state.my_name
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔥 열공 시작", use_container_width=True):
                update_db_status(st.session_state.invite_code, my_name, "🔥 열공 중"); st.rerun()
        with c2:
            if st.button("✅ 휴식/종료", use_container_width=True):
                update_db_status(st.session_state.invite_code, my_name, "✅ 대기 중"); st.rerun()

        st.divider()
        # AI 상담소
        st.subheader("💡 AI 진로 상담소")
        # 폼(form)을 사용하여 버튼 클릭 시에만 AI 호출
        with st.form("career_form"):
            career_q = st.text_area("고민 내용을 적어주세요")
            submit = st.form_submit_button("🔮 상담 시작")
            
            if submit:
                if career_q:
                    if model:
                        with st.spinner("AI 상담사가 분석 중..."):
                            try:
                                resp = model.generate_content(f"커리어 상담가로서 다음 질문에 답해줘: {career_q}")
                                st.session_state.career_result = resp.text
                            except Exception as e:
                                st.error(f"상담 중 오류: {e}")
                    else:
                        st.error("AI 모델이 연결되지 않았습니다. API 키를 다시 확인해 주세요.")
                else:
                    st.warning("내용을 입력해 주세요.")

        if st.session_state.career_result:
            st.success("🤖 AI 상담 결과")
            st.write(st.session_state.career_result)
            if st.button("결과 닫기"):
                st.session_state.career_result = None; st.rerun()
