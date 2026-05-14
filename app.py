import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. 서비스 연결 초기화 (404 에러 완벽 차단 버전) ---
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        
        # Supabase 연결
        s = create_client(s_url, s_key)
        
        # Gemini 설정
        genai.configure(api_key=g_key)
        
        # [해결 포인트] 모델 이름을 명시적으로 최신 버전으로 지정합니다.
        # 'models/' 접두사를 붙이거나 떼는 방식을 루프로 시도하여 404를 방지합니다.
        m = None
        target_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'models/gemini-1.5-flash']
        
        for model_id in target_models:
            try:
                temp_model = genai.GenerativeModel(model_id)
                # 실제로 텍스트 생성이 가능한지 테스트 (성공 시 루프 탈출)
                temp_model.generate_content("hi", generation_config={"max_output_tokens": 1})
                m = temp_model
                break
            except Exception:
                continue
                
        if m is None:
            st.error("🚨 사용 가능한 Gemini 모델을 찾을 수 없습니다. API 키의 활성화 상태를 확인하세요.")
            
        return s, m
    except Exception as e:
        st.error(f"🚨 시스템 초기화 에러: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 데이터 관리 유틸리티 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'career_result' not in st.session_state: st.session_state.career_result = None

def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except: return None

def update_db(code, column, value):
    try:
        supabase.table("team").update({column: value}).eq("invite_code", code).execute()
    except Exception as e:
        st.error(f"DB 업데이트 실패: {e}")

# --- 3. UI 화면 ---

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 리스트")
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        t_n = st.text_input("새 팀 이름")
        u_n = st.text_input("닉네임(생성)")
        if st.button("팀 만들기"):
            if t_n and u_n:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기"}],
                    "subjects": {u_n: ["공부 시작"]}, "posts": []
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()
    with c2:
        code_in = st.text_input("참여 코드")
        u_n_in = st.text_input("닉네임(참여)")
        if st.button("팀 참여하기"):
            data = get_team_data(code_in)
            if data:
                m_list = data.get('members', [])
                if not any(m['name'] == u_n_in for m in m_list):
                    m_list.append({"name": u_n_in, "status": "✅ 대기"})
                    update_db(code_in, "members", m_list)
                st.session_state.my_teams[code_in] = data['team_name']
                st.session_state.update({"invite_code": code_in, "my_name": u_n_in, "page": "dashboard"}); st.rerun()

# [대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=25000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["👥 팀 현황", "📅 AI 일정", "📋 게시판", "💡 상담소"])
        if st.sidebar.button("⬅️ 메인으로"): st.session_state.page = 'gate'; st.rerun()

        if menu == "👥 팀 현황":
            st.subheader(f"👥 실시간 상태 ({st.session_state.my_name})")
            cols = st.columns(4)
            for i, m in enumerate(data.get('members', [])):
                with cols[i % 4]: st.info(f"**{m['name']}**\n{m['status']}")
            st.divider()
            if st.button("🚀 공부 시작", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == st.session_state.my_name: m['status'] = "🔥 열공 중"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()
            if st.button("✅ 휴식하기", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()

        elif menu == "📅 AI 일정":
            st.subheader("🗓️ AI 스케줄러")
            todo = st.text_area("오늘 할 일")
            if st.button("일정 생성") and model:
                with st.spinner("생성 중..."):
                    res = model.generate_content(f"오늘 할 일: {todo}. 효율적인 시간표를 짜줘.")
                    st.write(res.text)

        elif menu == "📋 게시판":
            st.subheader("📋 게시판")
            cat = st.radio("카테고리", ["질문", "자유"], horizontal=True)
            with st.form("post_f"):
                p_t = st.text_input("제목"); p_c = st.text_area("내용")
                if st.form_submit_button("등록"):
                    posts = data.get('posts', []) or []
                    posts.append({"type": cat, "title": p_t, "content": p_c, "author": st.session_state.my_name, "date": datetime.now().strftime("%H:%M")})
                    update_db(st.session_state.invite_code, "posts", posts); st.rerun()
            for p in reversed(data.get('posts', []) or []):
                if p['type'] == cat:
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

        elif menu == "💡 상담소":
            st.subheader("💡 AI 진로 상담소")
            q = st.text_area("고민을 적어주세요")
            if st.button("🔮 상담 시작", use_container_width=True):
                if q and model:
                    with st.spinner("분석 중..."):
                        try:
                            resp = model.generate_content(f"커리어 상담가로서 조언해줘: {q}")
                            st.session_state.career_result = resp.text
                            st.rerun()
                        except Exception as e: st.error(f"상담 에러: {e}")
            if st.session_state.career_result:
                st.success("🤖 AI 상담 결과")
                st.markdown(st.session_state.career_result)
                if st.button("결과 닫기"): st.session_state.career_result = None; st.rerun()
