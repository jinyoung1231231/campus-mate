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
        
        # 모델 설정 (가장 호환성 높은 이름 시도)
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

# --- 2. 세션 및 유틸리티 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""

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

# --- 3. 화면 UI 로직 ---

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    
    if st.session_state.my_teams:
        st.subheader("🏠 참여 중인 팀")
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 생성")
        t_n = st.text_input("새 팀 이름", key="create_t")
        u_n = st.text_input("내 닉네임", key="create_u")
        if st.button("팀 만들기"):
            if t_n and u_n:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기"}],
                    "subjects": {u_n: ["자유 공부"]}, "posts": []
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
        code_in = st.text_input("참여 코드", key="join_c")
        u_n_in = st.text_input("내 닉네임", key="join_u")
        if st.button("팀 들어가기"):
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
        st.sidebar.caption(f"나의 이름: {st.session_state.my_name}")
        menu = st.sidebar.radio("이동할 곳", ["👥 팀 현황", "🗓️ AI 일정", "📋 게시판", "💡 상담소"])
        if st.sidebar.button("⬅️ 메인으로"): st.session_state.page = 'gate'; st.rerun()

        # 1. 팀 현황
        if menu == "👥 팀 현황":
            st.title("👥 팀원 실시간 상태")
            st.info(f"초대 코드: {st.session_state.invite_code}")
            cols = st.columns(4)
            for i, m in enumerate(data.get('members', [])):
                with cols[i % 4]:
                    st.info(f"**{m['name']}**\n{m['status']}")
            
            st.divider()
            # 공부 버튼
            if st.button("🚀 공부 시작", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == st.session_state.my_name: m['status'] = "🔥 열공 중"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()
            if st.button("✅ 공부 종료/휴식", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()

        # 2. AI 일정
        elif menu == "🗓️ AI 일정":
            st.title("🗓️ AI 스케줄러")
            todo = st.text_area("오늘의 목표")
            if st.button("스케줄 생성") and model:
                with st.spinner("생성 중..."):
                    res = model.generate_content(f"오늘 목표: {todo}. 시간표 짜줘.")
                    st.write(res.text)

        # 3. 게시판 (에러 수정된 곳!)
        elif menu == "📋 게시판":
            st.title("📋 커뮤니티")
            cat = st.radio("카테고리", ["질문", "자유"], horizontal=True)
            
            with st.form("post_form", clear_on_submit=True):
                p_title = st.text_input("제목")
                p_content = st.text_area("내용")
                if st.form_submit_button("등록"):
                    if p_title and p_content:
                        # 기존 posts 데이터를 가져올 때 None이면 빈 리스트로 처리
                        posts = data.get('posts') if data.get('posts') is not None else []
                        new_post = {
                            "type": cat, "title": p_title, "content": p_content,
                            "author": st.session_state.my_name, "date": datetime.now().strftime("%H:%M")
                        }
                        posts.append(new_post)
                        update_db(st.session_state.invite_code, "posts", posts)
                        st.success("게시글이 등록되었습니다!"); st.rerun()

            st.divider()
            posts = data.get('posts', []) if data.get('posts') is not None else []
            for p in reversed(posts):
                if p['type'] == cat:
                    with st.expander(f"{p['title']} - {p['author']} ({p['date']})"):
                        st.write(p['content'])

        # 4. 상담소
        elif menu == "💡 상담소":
            st.title("💡 AI 진로 상담")
            q = st.text_area("고민을 적어주세요")
            if st.button("상담 시작") and model:
                with st.spinner("분석 중..."):
                    res = model.generate_content(f"조언해줘: {q}")
                    st.info(res.text)
