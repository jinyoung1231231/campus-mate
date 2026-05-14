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
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = "" 

def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except: return None

def update_db(code, column, value):
    try:
        supabase.table("team").update({column: value}).eq("invite_code", code).execute()
    except Exception as e: st.error(f"DB 오류: {e}")

# --- 3. UI 로직 ---

# [게이트웨이: 팀 생성/참여]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} 입장 ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀 이름", key="tn")
        un = st.text_input("닉네임", key="un")
        if st.button("방 만들기"):
            if tn and un:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({"invite_code": code, "team_name": tn, "members": [{"name": un, "status": "✅ 대기"}], "subjects": {un: []}, "posts": []}).execute()
                st.session_state.my_teams[code] = tn
                st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
        ci = st.text_input("코드", key="ci")
        ui = st.text_input("닉네임", key="ui")
        if st.button("참여하기"):
            data = get_team_data(ci)
            if data:
                ml = data.get('members', [])
                sl = data.get('subjects', {}) or {}
                if not any(m['name'] == ui for m in ml):
                    ml.append({"name": ui, "status": "✅ 대기"})
                    sl[ui] = []
                    update_db(ci, "members", ml); update_db(ci, "subjects", sl)
                st.session_state.my_teams[ci] = data['team_name']
                st.session_state.update({"invite_code": ci, "my_name": ui, "page": "dashboard"}); st.rerun()

# [대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 학습 관리 & AI 도구", "📋 커뮤니티", "💡 진로상담"])
        
        st.sidebar.divider()
        st.sidebar.subheader("👥 팀원 실시간 현황")
        for m in data.get('members', []):
            st.sidebar.write(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']}: {m['status']}")
        
        if st.sidebar.button("⬅️ 메인으로"): st.session_state.page = 'gate'; st.rerun()

        # 메인 레이아웃 분할
        col_main, col_ai = st.columns([1, 1])

        with col_main:
            if menu == "📚 학습 관리 & AI 도구":
                st.header("📚 과목 학습 & AI 플래너")
                my_name = st.session_state.my_name
                my_subs = data.get('subjects', {}).get(my_name, [])

                with st.expander("➕ 과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data.get('subjects', {}); all_s[my_name] = my_subs
                        update_db(st.session_state.invite_code, "subjects", all_s); st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 과목 선택", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("강의자료/교안 업로드 (PDF/TXT)", type=['pdf', 'txt'], key=f"file_{sel_sub}")
                    
                    # --- 핵심: 일정 짜기 버튼 복구 ---
                    if st.button("🗓️ 이 자료로 일정 짜줘", use_container_width=True):
                        if up_file and model:
                            with st.spinner("AI가 일정을 구성 중입니다..."):
                                text = up_file.read().decode("utf-8", errors="ignore")
                                res = model.generate_content(f"다음 학습 자료를 바탕으로 효율적인 주간 학습 일정을 짜줘:\n{text[:3000]}")
                                st.session_state.ai_ans = res.text
                                st.rerun()
                        else:
                            st.warning("파일을 먼저 업로드해주세요!")

                    st.divider()
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == my_name: m['status'] = f"🔥 {sel_sub} 중"
                            update_db(st.session_state.invite_code, "members", ml); st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 퀴즈", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == my_name: m['status'] = "✅ 대기"
                            update_db(st.session_state.invite_code, "members", ml)
                            
                            # 공부 종료 후 퀴즈 생성
                            if up_file and model:
                                with st.spinner("퀴즈 생성 중..."):
                                    up_file.seek(0) # 파일 포인터 리셋
                                    text = up_file.read().decode("utf-8", errors="ignore")
                                    res = model.generate_content(f"이 내용에서 중요한 내용으로 퀴즈 3개만 내줘(정답 포함):\n{text[:3000]}")
                                    st.session_state.ai_ans = res.text
                            else:
                                st.session_state.ai_ans = "공부 종료! 파일이 없어 퀴즈 대신 응원 한마디: 오늘도 고생했어!"
                            st.rerun()

            elif menu == "📋 커뮤니티":
                st.header("📋 팀 게시판")
                with st.form("post_form", clear_on_submit=True):
                    t = st.text_input("제목")
                    c = st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data.get('posts', []) or []
                        ps.append({"title": t, "content": c, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        update_db(st.session_state.invite_code, "posts", ps); st.rerun()
                for p in reversed(data.get('posts', []) or []):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민을 입력하세요")
                if st.button("상담 시작"):
                    if q and model:
                        with st.spinner("AI 상담 중..."):
                            res = model.generate_content(f"커리어 상담가로서 조언해줘: {q}")
                            st.session_state.ai_ans = res.text
                            st.rerun()

        with col_ai:
            # --- AI 답변 전용 섹션 ---
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.success("AI의 분석 결과입니다.")
                st.write(st.session_state.ai_ans)
                if st.button("결과 지우기"):
                    st.session_state.ai_ans = ""; st.rerun()
            else:
                st.info("여기에 AI의 일정 추천, 퀴즈, 상담 답변이 표시됩니다.")
