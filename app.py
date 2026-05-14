import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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

# --- 2. 데이터 유틸리티 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_response' not in st.session_state: st.session_state.ai_response = "" # AI 전용 답변 칸

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

# [게이트웨이 생략 - 이전과 동일]
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
        t_n = st.text_input("새 팀 이름")
        u_n = st.text_input("내 닉네임(생성)")
        if st.button("팀 생성"):
            if t_n and u_n:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": t_n,
                    "members": [{"name": u_n, "status": "✅ 대기"}],
                    "subjects": {u_n: []}, # 사용자별 과목 리스트
                    "posts": []
                }).execute()
                st.session_state.my_teams[code] = t_n
                st.session_state.update({"invite_code": code, "my_name": u_n, "page": "dashboard"}); st.rerun()
    with c2:
        code_in = st.text_input("초대 코드")
        u_n_in = st.text_input("내 닉네임(참여)")
        if st.button("팀 참여"):
            data = get_team_data(code_in)
            if data:
                m_list = data.get('members', [])
                all_subs = data.get('subjects', {})
                if not any(m['name'] == u_n_in for m in m_list):
                    m_list.append({"name": u_n_in, "status": "✅ 대기"})
                    all_subs[u_n_in] = []
                    update_db(code_in, "members", m_list)
                    update_db(code_in, "subjects", all_subs)
                st.session_state.my_teams[code_in] = data['team_name']
                st.session_state.update({"invite_code": code_in, "my_name": u_n_in, "page": "dashboard"}); st.rerun()

# [메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="refresh") # 갱신 주기 연장
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.title(f"🏫 {data['team_name']}")
        
        # --- 사이드바: 팀원 현황 ---
        st.sidebar.subheader("👥 팀원 실시간 상태")
        for m in data.get('members', []):
            st.sidebar.info(f"**{m['name']}**: {m['status']}")
        if st.sidebar.button("⬅️ 팀 목록"): st.session_state.page = 'gate'; st.rerun()

        # --- 메인 레이아웃: 2컬럼 ---
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.subheader("📚 과목 및 학습 자료 관리")
            my_name = st.session_state.my_name
            my_subjects = data.get('subjects', {}).get(my_name, [])

            # 과목 추가
            with st.expander("➕ 새 과목 추가하기"):
                new_sub = st.text_input("과목명 입력")
                if st.button("과목 등록"):
                    if new_sub and new_sub not in [s['name'] for s in my_subjects]:
                        my_subjects.append({"name": new_sub, "syllabus": ""})
                        all_subs = data.get('subjects', {})
                        all_subs[my_name] = my_subjects
                        update_db(st.session_state.invite_code, "subjects", all_subs); st.rerun()

            # 과목별 자료 업로드 및 일정 생성
            if my_subjects:
                sub_names = [s['name'] for s in my_subjects]
                selected_sub = st.selectbox("관리할 과목 선택", sub_names)
                
                # 자료 입력 (강의계획서 등)
                syllabus_text = st.text_area(f"[{selected_sub}] 강의계획서 또는 학습 내용 입력", 
                                            placeholder="주차별 학습 목표나 시험 범위를 적어주세요.")
                
                c1, c2 = st.columns(2)
                if c1.button(f"🚀 {selected_sub} 열공 시작"):
                    m_list = data['members']
                    for m in m_list:
                        if m['name'] == my_name: m['status'] = f"🔥 {selected_sub} 중"
                    update_db(st.session_state.invite_code, "members", m_list); st.rerun()
                
                if c2.button("🏁 자료 기반 일정 생성"):
                    if syllabus_text and model:
                        with st.spinner("AI가 강의계획서를 분석하여 일정을 짜고 있습니다..."):
                            prompt = f"다음은 {selected_sub} 과목의 강의 정보입니다: {syllabus_text}. 이 내용을 바탕으로 효율적인 4주 학습 스케줄을 짜줘."
                            res = model.generate_content(prompt)
                            st.session_state.ai_response = res.text
                            st.rerun()

            st.divider()
            # 진로 상담소 입력창
            st.subheader("💡 AI 진로 상담소")
            career_q = st.text_area("고민을 적어주세요")
            if st.button("🔮 상담 시작"):
                if career_q and model:
                    with st.spinner("상담사 답변 생성 중..."):
                        res = model.generate_content(f"전문 커리어 상담가로서 다음 고민에 답변해줘: {career_q}")
                        st.session_state.ai_response = res.text
                        st.rerun()

        with col_right:
            # --- AI 전용 답변 칸 ---
            st.subheader("🤖 AI Response")
            if st.session_state.ai_response:
                st.info(st.session_state.ai_response)
                if st.button("답변 지우기"):
                    st.session_state.ai_response = ""
                    st.rerun()
            else:
                st.write("AI의 답변이 여기에 표시됩니다. 일정 생성이나 상담을 시작해보세요!")
            
            st.divider()
            # 게시판 요약
            st.subheader("📝 최근 게시판")
            posts = data.get('posts', [])
            for p in reversed(posts[-3:]): # 최근 3개만
                st.caption(f"**{p['author']}**: {p['title']}")
