import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. 서비스 연결 초기화 ---
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        
        m = None
        for name in ['gemini-1.5-flash', 'gemini-pro']:
            try:
                temp = genai.GenerativeModel(name)
                temp.generate_content("hi", generation_config={"max_output_tokens": 1})
                m = temp
                break
            except: continue
        return s, m
    except Exception as e:
        st.error(f"연결 에러: {e}")
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
    st.caption("AI 기반 멀티 스터디 커뮤니티")
    
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 요새")
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 생성")
        t_n = st.text_input("새 팀 이름")
        u_n = st.text_input("닉네임 (생성)")
        if st.button("팀 만들기"):
            if t_n and u_n:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                # [해결 포인트] 모든 컬럼에 기본 데이터를 명시적으로 넣음
                supabase.table("team").insert({
                    "invite_code": code,
                    "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기"}],
                    "subjects": {u_n: ["공부 시작하기"]},
                    "posts": []
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()

    with c2:
        st.subheader("🔗 참여")
        code_in = st.text_input("참여 코드")
        u_n_in = st.text_input("닉네임 (참여)")
        if st.button("참여 확정"):
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
    st_autorefresh(interval=20000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        st.sidebar.caption(f"접속: {st.session_state.my_name}")
        menu = st.sidebar.radio("메뉴", ["👥 팀 현황", "📅 AI 일정", "📋 게시판", "💡 상담소"])
        if st.sidebar.button("⬅️ 메인으로"): st.session_state.page = 'gate'; st.rerun()

        # 1. 팀 현황
        if menu == "👥 팀 현황":
            st.title("👥 실시간 현황")
            st.info(f"초대 코드: {st.session_state.invite_code}")
            cols = st.columns(4)
            for i, m in enumerate(data.get('members', [])):
                with cols[i % 4]:
                    st.info(f"**{m['name']}**\n{m['status']}")
            
            st.divider()
            if st.button("🚀 공부 시작", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == st.session_state.my_name: m['status'] = "🔥 열공 중"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()
            if st.button("✅ 휴식/종료", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()

        # 2. AI 일정
        elif menu == "📅 AI 일정":
            st.title("🗓️ AI 스케줄러")
            todo = st.text_area("오늘 목표")
            if st.button("시간표 짜줘") and model:
                with st.spinner("생각 중..."):
                    res = model.generate_content(f"오늘 목표: {todo}. 시간표 짜줘.")
                    st.write(res.text)

        # 3. 게시판
        elif menu == "📋 게시판":
            st.title("📋 커뮤니티")
            cat = st.radio("카테고리", ["질문", "자유"], horizontal=True)
            
            with st.form("post_form"):
                p_title = st.text_input("제목")
                p_content = st.text_area("내용")
                if st.form_submit_button("등록"):
                    if p_title and p_content:
                        posts = data.get('posts') if data.get('posts') is not None else []
                        posts.append({
                            "type": cat, "title": p_title, "content": p_content,
                            "author": st.session_state.my_name, "date": datetime.now().strftime("%H:%M")
                        })
                        update_db(st.session_state.invite_code, "posts", posts); st.rerun()

            st.divider()
            posts = data.get('posts', []) if data.get('posts') is not None else []
            for p in reversed(posts):
                if p['type'] == cat:
                    with st.expander(f"{p['title']} - {p['author']}"):
                        st.write(p['content'])

        # 4. 상담소
        elif menu == "💡 상담소":
            st.title("💡 AI 진로 상담")
            q = st.text_area("고민 내용을 적어주세요")
            
            # [수정된 상담 로직] 세션 상태를 활용하여 끊김 방지
            if st.button("🔮 상담 시작", use_container_width=True):
                if q:
                    if model:
                        with st.spinner("AI 상담사가 분석 중입니다..."):
                            try:
                                resp = model.generate_content(f"커리어 전문가로서 조언해줘: {q}")
                                st.session_state.career_result = resp.text
                                st.rerun()
                            except Exception as e:
                                st.error(f"상담 실행 중 에러: {e}")
                    else:
                        st.error("AI 모델 연결 실패")
                else:
                    st.warning("내용을 입력하세요")

            if st.session_state.career_result:
                st.success("🤖 AI 상담 결과")
                st.markdown(st.session_state.career_result)
                if st.button("결과 닫기"):
                    st.session_state.career_result = None
                    st.rerun()
