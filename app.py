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
        for name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-pro']:
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

# --- 2. 데이터 유틸리티 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'quiz_result' not in st.session_state: st.session_state.quiz_result = None

def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except: return None

def update_db(code, column, value):
    try:
        supabase.table("team").update({column: value}).eq("invite_code", code).execute()
    except Exception as e: st.error(f"DB 업데이트 실패: {e}")

# --- 3. UI 화면 ---

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 요새")
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        t_n = st.text_input("새 팀 이름")
        u_n = st.text_input("내 닉네임 (생성)")
        if st.button("팀 생성"):
            if t_n and u_n:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기", "plan": ""}],
                    "posts": []
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()
    with c2:
        code_in = st.text_input("초대 코드")
        u_n_in = st.text_input("내 닉네임 (참여)")
        if st.button("팀 참여"):
            data = get_team_data(code_in)
            if data:
                m_list = data.get('members', [])
                if not any(m['name'] == u_n_in for m in m_list):
                    m_list.append({"name": u_n_in, "status": "✅ 대기", "plan": ""})
                    update_db(code_in, "members", m_list)
                st.session_state.my_teams[code_in] = data['team_name']
                st.session_state.update({"invite_code": code_in, "my_name": u_n_in, "page": "dashboard"}); st.rerun()

# [메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=15000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.sidebar.markdown(f"### 👤 {st.session_state.my_name}")
        menu = st.sidebar.radio("메뉴", ["🏠 대시보드", "📋 게시판", "💡 상담소"])
        if st.sidebar.button("⬅️ 팀 목록"): st.session_state.page = 'gate'; st.rerun()

        if menu == "🏠 대시보드":
            # --- 상단: 팀원 실시간 현황 & 일정 ---
            st.subheader("👥 팀원 현황 및 오늘의 계획")
            members = data.get('members', [])
            for m in members:
                col_name, col_status, col_plan = st.columns([1, 1, 3])
                col_name.markdown(f"**{m['name']}**")
                col_status.info(m['status'])
                col_plan.caption(f"📅 계획: {m['plan'] if m['plan'] else '계획 미설정'}")

            st.divider()

            # --- 중간: 나의 학습 제어판 ---
            st.subheader("📝 나의 학습 제어판")
            c1, c2 = st.columns([2, 1])
            
            with c1:
                my_plan = st.text_input("오늘의 목표 설정", placeholder="예: 수학 1단원 풀기, 영단어 외우기")
                if st.button("📅 계획 업데이트"):
                    for m in members:
                        if m['name'] == st.session_state.my_name: m['plan'] = my_plan
                    update_db(st.session_state.invite_code, "members", members); st.rerun()
            
            with c2:
                if st.button("🚀 공부 시작", use_container_width=True):
                    for m in members:
                        if m['name'] == st.session_state.my_name: m['status'] = "🔥 열공 중"
                    update_db(st.session_state.invite_code, "members", members); st.rerun()
                if st.button("✅ 휴식/종료", use_container_width=True):
                    for m in members:
                        if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                    update_db(st.session_state.invite_code, "members", members); st.rerun()

            st.divider()

            # --- 하단: 파일 업로드 및 AI 퀴즈 ---
            st.subheader("🏁 공부 확인 (AI 퀴즈)")
            up_file = st.file_uploader("공부한 자료(TXT/PDF)를 올려주세요.", type=['txt', 'pdf'])
            
            if st.button("🏁 공부 끝! 퀴즈 내줘"):
                if up_file and model:
                    with st.spinner("자료를 분석하여 퀴즈를 생성 중입니다..."):
                        content = up_file.read().decode("utf-8") if up_file.type == "text/plain" else "PDF 데이터 분석 요청"
                        res = model.generate_content(f"다음 내용을 바탕으로 핵심 퀴즈 3개와 정답을 만들어줘: {content[:3000]}")
                        st.session_state.quiz_result = res.text
                        st.rerun()
                elif not up_file:
                    st.warning("파일을 먼저 업로드해 주세요!")

            if st.session_state.quiz_result:
                st.success("🤖 AI 검증 퀴즈")
                st.write(st.session_state.quiz_result)
                if st.button("퀴즈 닫기"): st.session_state.quiz_result = None; st.rerun()

        # [게시판/상담소는 이전 기능 유지]
        elif menu == "📋 게시판":
            st.subheader("📝 커뮤니티")
            with st.form("post_f"):
                t = st.text_input("제목"); c = st.text_area("내용")
                if st.form_submit_button("등록"):
                    ps = data.get('posts', [])
                    ps.append({"title": t, "content": c, "author": st.session_state.my_name, "date": datetime.now().strftime("%H:%M")})
                    update_db(st.session_state.invite_code, "posts", ps); st.rerun()
            for p in reversed(data.get('posts', [])):
                with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

        elif menu == "💡 상담소":
            st.subheader("💡 진로 상담")
            q = st.text_area("고민을 적어주세요")
            if st.button("상담 시작") and model:
                with st.spinner("생각 중..."):
                    res = model.generate_content(f"조언해줘: {q}")
                    st.info(res.text)
