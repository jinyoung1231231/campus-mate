import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. 서비스 연결 및 AI 진단 로직 ---
def init_connection():
    try:
        # Secrets 로드 확인
        s_url = st.secrets.get("SUPABASE_URL")
        s_key = st.secrets.get("SUPABASE_KEY")
        g_key = st.secrets.get("GEMINI_API_KEY")
        
        if not all([s_url, s_key, g_key]):
            st.error("⚠️ Secrets 설정(URL, KEY, API_KEY)을 모두 확인해주세요.")
            return None, None
            
        # Supabase 연결
        s = create_client(s_url, s_key)
        
        # Gemini 설정
        genai.configure(api_key=g_key)
        
        # [해결 핵심] 사용 가능한 최신 모델 자동 탐색
        m = None
        try:
            # 1.5-flash 모델 시도 (가장 권장됨)
            m = genai.GenerativeModel('gemini-1.5-flash')
            # 연결 테스트
            m.generate_content("hi", generation_config={"max_output_tokens": 1})
        except Exception:
            try:
                # 실패 시 1.0-pro 모델로 대체 시도
                m = genai.GenerativeModel('gemini-pro')
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
            except Exception as e:
                st.error(f"🚨 AI 모델 최종 연결 실패: {e}")
                m = None
                
        return s, m
    except Exception as e:
        st.error(f"🚨 시스템 초기화 에러: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 및 데이터 관리 ---
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
                    "subjects": {u_n: ["기본 공부"]}, "posts": []
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
    st_autorefresh(interval=20000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("이동", ["👥 팀 현황", "📅 AI 일정", "📋 게시판", "💡 상담소"])
        if st.sidebar.button("⬅️ 메인"): st.session_state.page = 'gate'; st.rerun()

        # 팀 현황
        if menu == "👥 팀 현황":
            st.subheader(f"👥 실시간 상태 ({st.session_state.my_name})")
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

        # AI 일정
        elif menu == "📅 AI 일정":
            st.subheader("🗓️ AI 스케줄러")
            todo = st.text_area("오늘 할 일")
            if st.button("일정 짜기") and model:
                with st.spinner("AI 분석 중..."):
                    res = model.generate_content(f"오늘 할 일: {todo}. 시간표 짜줘.")
                    st.write(res.text)

        # 게시판
        elif menu == "📋 게시판":
            st.subheader("📋 우리들의 공간")
            cat = st.radio("카테고리", ["질문", "자유"], horizontal=True)
            with st.form("post_form"):
                p_t = st.text_input("제목")
                p_c = st.text_area("내용")
                if st.form_submit_button("등록"):
                    posts = data.get('posts', []) or []
                    posts.append({"type": cat, "title": p_t, "content": p_c, "author": st.session_state.my_name, "date": datetime.now().strftime("%H:%M")})
                    update_db(st.session_state.invite_code, "posts", posts); st.rerun()
            for p in reversed(data.get('posts', []) or []):
                if p['type'] == cat:
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

        # AI 상담소 (수정된 로직)
        elif menu == "💡 상담소":
            st.subheader("💡 AI 진로 상담소")
            q = st.text_area("고민 내용을 입력하세요")
            if st.button("🔮 상담 시작", use_container_width=True):
                if q and model:
                    with st.spinner("AI 상담사가 답변을 작성하고 있습니다..."):
                        try:
                            resp = model.generate_content(f"커리어 상담 전문가로서 조언해줘: {q}")
                            st.session_state.career_result = resp.text
                            st.rerun()
                        except Exception as e: st.error(f"상담 중 에러: {e}")
            if st.session_state.career_result:
                st.success("🤖 AI 상담 결과")
                st.markdown(st.session_state.career_result)
                if st.button("결과 닫기"): st.session_state.career_result = None; st.rerun()
