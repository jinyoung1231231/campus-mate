import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import io

# --- 1. 서비스 연결 및 초기화 ---
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        
        m = None
        for name in ['gemini-1.5-flash', 'gemini-1.5-pro']:
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

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_response' not in st.session_state: st.session_state.ai_response = ""

def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except: return None

def update_db(code, column, value):
    try:
        supabase.table("team").update({column: value}).eq("invite_code", code).execute()
    except Exception as e: st.error(f"DB 업데이트 실패: {e}")

# --- 3. UI 화면 로직 ---

# [게이트웨이: 팀 생성/참여]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        t_n = st.text_input("새 팀 이름", key="n_t")
        u_n = st.text_input("내 닉네임", key="n_u")
        if st.button("생성 완료"):
            if t_n and u_n:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기"}],
                    "subjects": {u_n: []}, "posts": []
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 팀 참여")
        code_in = st.text_input("초대 코드", key="i_c")
        u_n_in = st.text_input("내 닉네임", key="i_u")
        if st.button("참여 완료"):
            data = get_team_data(code_in)
            if data:
                m_list = data.get('members', [])
                all_subs = data.get('subjects', {}) or {}
                if not any(m['name'] == u_n_in for m in m_list):
                    m_list.append({"name": u_n_in, "status": "✅ 대기"})
                    all_subs[u_n_in] = []
                    update_db(code_in, "members", m_list)
                    update_db(code_in, "subjects", all_subs)
                st.session_state.my_teams[code_in] = data['team_name']
                st.session_state.update({"invite_code": code_in, "my_name": u_n_in, "page": "dashboard"}); st.rerun()

# [메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        # [메뉴 복구]
        menu = st.sidebar.radio("메뉴 이동", ["👥 팀 현황", "📚 과목&파일 분석", "📋 커뮤니티 게시판", "💡 AI 진로 상담"])
        
        if st.sidebar.button("⬅️ 팀 목록으로"): st.session_state.page = 'gate'; st.rerun()

        # 1. 팀 현황
        if menu == "👥 팀 현황":
            st.subheader("👥 팀원 실시간 상태")
            cols = st.columns(4)
            for i, m in enumerate(data.get('members', [])):
                with cols[i % 4]:
                    st.info(f"**{m['name']}**\n{m['status']}")
            
            st.divider()
            my_name = st.session_state.my_name
            if st.button("🚀 공부 시작 (열공 중으로 변경)", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == my_name: m['status'] = "🔥 열공 중"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()
            if st.button("✅ 휴식/종료 (대기 중으로 변경)", use_container_width=True):
                m_list = data['members']
                for m in m_list:
                    if m['name'] == my_name: m['status'] = "✅ 대기"
                update_db(st.session_state.invite_code, "members", m_list); st.rerun()

        # 2. 과목 및 파일 분석 (핵심 기능)
        elif menu == "📚 과목&파일 분석":
            st.subheader("📚 과목별 학습자료 분석 및 일정 생성")
            my_name = st.session_state.my_name
            all_subs_data = data.get('subjects', {}) or {}
            my_subs = all_subs_data.get(my_name, [])

            with st.expander("➕ 새 과목 추가"):
                new_sub = st.text_input("과목명")
                if st.button("등록"):
                    if new_sub:
                        my_subs.append({"name": new_sub})
                        all_subs_data[my_name] = my_subs
                        update_db(st.session_state.invite_code, "subjects", all_subs_data); st.rerun()

            if my_subs:
                selected_sub = st.selectbox("파일을 분석할 과목 선택", [s['name'] for s in my_subs])
                uploaded_file = st.file_uploader(f"[{selected_sub}] 강의계획서 또는 교안 업로드 (TXT/PDF)", type=['txt', 'pdf'])
                
                if st.button("📄 파일 읽고 일정 짜주기"):
                    if uploaded_file and model:
                        with st.spinner("AI가 파일을 정독하고 있습니다..."):
                            # 파일 읽기 로직
                            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
                            file_content = stringio.read()
                            
                            prompt = f"다음은 {selected_sub} 과목의 학습 자료 내용이야: \n{file_content[:4000]}\n 이 내용을 바탕으로 주차별 학습 일정과 핵심 요약을 만들어줘."
                            res = model.generate_content(prompt)
                            st.session_state.ai_response = res.text
                            st.rerun()
            
            if st.session_state.ai_response:
                st.success("🤖 AI 분석 결과")
                st.markdown(st.session_state.ai_response)
                if st.button("결과 지우기"): st.session_state.ai_response = ""; st.rerun()

        # 3. 게시판 (글쓰기 복구)
        elif menu == "📋 커뮤니티 게시판":
            st.subheader("📋 팀 커뮤니티 게시판")
            with st.form("board_form", clear_on_submit=True):
                p_title = st.text_input("제목")
                p_content = st.text_area("내용")
                if st.form_submit_button("게시글 등록"):
                    if p_title and p_content:
                        posts = data.get('posts', []) or []
                        posts.append({
                            "title": p_title, "content": p_content,
                            "author": st.session_state.my_name,
                            "date": datetime.now().strftime("%m/%d %H:%M")
                        })
                        update_db(st.session_state.invite_code, "posts", posts); st.rerun()
            
            st.divider()
            posts = data.get('posts', []) or []
            for p in reversed(posts):
                with st.expander(f"{p['title']} - {p['author']} ({p['date']})"):
                    st.write(p['content'])

        # 4. 진로 상담
        elif menu == "💡 AI 진로 상담":
            st.subheader("💡 AI 커리어 상담소")
            q = st.text_area("고민을 상세히 적어주세요.")
            if st.button("상담 시작"):
                if q and model:
                    with st.spinner("AI 상담사가 분석 중..."):
                        res = model.generate_content(f"커리어 상담가로서 답변해줘: {q}")
                        st.session_state.ai_response = res.text
                        st.rerun()
            if st.session_state.ai_response:
                st.info(st.session_state.ai_response)
