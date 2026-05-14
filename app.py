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
        
        # 모델 설정
        m = None
        try:
            m = genai.GenerativeModel('gemini-1.5-flash')
            m.generate_content("hi", generation_config={"max_output_tokens": 1})
        except:
            m = None
        return s, m
    except Exception as e:
        st.error(f"연결 에러: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""

# DB 유틸리티
def get_team_data(code):
    res = supabase.table("team").select("*").eq("invite_code", code).execute()
    return res.data[0] if res.data else None

def update_db(code, column, value):
    supabase.table("team").update({column: value}).eq("invite_code", code).execute()

# --- 3. UI 화면 로직 ---

# [게이트웨이: 팀 선택/생성]
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
        if st.button("🆕 팀 생성"):
            t_n = st.text_input("팀 이름")
            u_n = st.text_input("닉네임 (생성)")
            if st.button("생성 확정"):
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기"}],
                    "subjects": {u_n: ["기본 공부"]},
                    "posts": [] # 게시판 데이터
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()
    with c2:
        if st.button("🔗 팀 참여"):
            code_in = st.text_input("코드 입력")
            u_n_in = st.text_input("닉네임 (참여)")
            if st.button("참여 확정"):
                data = get_team_data(code_in)
                if data:
                    m_list = data['members']
                    m_list.append({"name": u_n_in, "status": "✅ 대기"})
                    update_db(code_in, "members", m_list)
                    st.session_state.my_teams[code_in] = data['team_name']
                    st.session_state.update({"invite_code": code_in, "my_name": u_n_in, "page": "dashboard"}); st.rerun()

# [메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=15000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.sidebar.header(f"👤 {st.session_state.my_name}")
        menu = st.sidebar.radio("메뉴 선택", ["👥 팀 현황", "📅 AI 일정 플래너", "📋 커뮤니티 게시판", "💡 진로 상담"])
        
        if st.sidebar.button("⬅️ 팀 나가기"): st.session_state.page = 'gate'; st.rerun()

        # --- 메뉴 1: 실시간 팀 현황 & 과목 관리 ---
        if menu == "👥 팀 현황":
            st.subheader("👥 팀원 실시간 상태")
            m_cols = st.columns(4)
            for i, m in enumerate(data['members']):
                with m_cols[i % 4]:
                    st.info(f"**{m['name']}**\n{m['status']}")
            
            st.divider()
            st.subheader("📚 나의 학습 관리")
            my_subs = data.get('subjects', {}).get(st.session_state.my_name, ["기본"])
            tabs = st.tabs(my_subs)
            for i, tab in enumerate(tabs):
                with tab:
                    s_n = my_subs[i]
                    c1, c2 = st.columns(2)
                    if c1.button(f"🚀 {s_n} 시작", key=f"s_{s_n}"):
                        m_list = data['members']
                        for m in m_list:
                            if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {s_n} 중"
                        update_db(st.session_state.invite_code, "members", m_list); st.rerun()
                    if c2.button(f"🏁 종료", key=f"e_{s_n}"):
                        m_list = data['members']
                        for m in m_list:
                            if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                        update_db(st.session_state.invite_code, "members", m_list); st.rerun()

        # --- 메뉴 2: AI 일정 플래너 ---
        elif menu == "📅 AI 일정 플래너":
            st.subheader("🗓️ AI 맞춤형 학습 계획")
            todo = st.text_area("오늘 공부해야 할 리스트를 적어주세요.", placeholder="예: 수학 문제집 20p, 영단어 50개, 파이썬 강의 2개")
            time_limit = st.slider("가용 시간 (시간)", 1, 12, 4)
            
            if st.button("🪄 AI 플랜 생성"):
                if model:
                    with st.spinner("최적의 일정을 계산 중..."):
                        res = model.generate_content(f"{time_limit}시간 동안 다음 할 일들을 효율적으로 배치한 시간표를 짜줘: {todo}")
                        st.success("AI 제안 스케줄")
                        st.write(res.text)

        # --- 메뉴 3: 커뮤니티 게시판 (질문/자유) ---
        elif menu == "📋 커뮤니티 게시판":
            st.subheader("📝 우리들의 공간")
            p_type = st.radio("카테고리", ["❓ 질문 게시판", "☕ 자유 게시판"], horizontal=True)
            
            with st.expander("✍️ 글 쓰기"):
                title = st.text_input("제목")
                content = st.text_area("내용")
                if st.button("등록"):
                    posts = data.get('posts', [])
                    posts.append({
                        "type": p_type, "title": title, "content": content,
                        "author": st.session_state.my_name, "date": datetime.now().strftime("%m/%d %H:%M")
                    })
                    update_db(st.session_state.invite_code, "posts", posts); st.rerun()
            
            st.divider()
            posts = data.get('posts', [])[::-1] # 최신순
            for p in posts:
                if p['type'] == p_type:
                    with st.chat_message("user" if p['type']=="❓ 질문 게시판" else "assistant"):
                        st.write(f"**{p['title']}** (작성자: {p['author']} | {p['date']})")
                        st.write(p['content'])

        # --- 메뉴 4: AI 진로 상담 ---
        elif menu == "💡 진로 상담":
            st.subheader("🔮 AI 커리어 상담소")
            q = st.text_area("진로나 취업, 공부 방향에 대한 고민을 나눠주세요.")
            if st.button("상담 받기"):
                if model:
                    with st.spinner("답변 생성 중..."):
                        res = model.generate_content(f"전문 커리어 컨설턴트로서 조언해줘: {q}")
                        st.info(res.text)
