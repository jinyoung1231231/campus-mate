import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader
import io

# --- 1. 서비스 연결 초기화 ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        return s, genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"연결 설정 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 초기화 (매우 중요) ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'temp_content' not in st.session_state: st.session_state.temp_content = ""

# --- 3. 데이터 보조 함수 ---
def extract_text(uploaded_file):
    text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        else:
            text = uploaded_file.getvalue().decode("utf-8")
    except: pass
    return text

def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except: return None

def update_db(code, column, value):
    try: supabase.table("team").update({column: value}).eq("invite_code", code).execute()
    except: pass

# --- 4. 메인 UI ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    # (게이트웨이 로직은 이전과 동일하므로 생략하거나 기존 코드 유지)
    # [참고: 팀 생성/참여 완료 시 st.session_state.page = 'dashboard'로 전환]
    c1, c2 = st.columns(2)
    with c1:
        tn = st.text_input("팀 이름")
        un = st.text_input("내 이름")
        if st.button("방 만들기"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({"invite_code": code, "team_name": tn, "members": [{"name": un, "status": "✅ 대기"}], "subjects": {un: []}, "posts": []}).execute()
            st.session_state.my_teams[code] = tn
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        ci = st.text_input("코드 입력")
        ui = st.text_input("내 이름 ")
        if st.button("참여하기"):
            data = get_team_data(ci)
            if data:
                ml = data.get('members', []); sl = data.get('subjects', {}) or {}
                if not any(m['name'] == ui for m in ml):
                    ml.append({"name": ui, "status": "✅ 대기"}); sl[ui] = []
                    update_db(ci, "members", ml); update_db(ci, "subjects", sl)
                st.session_state.my_teams[ci] = data['team_name']
                st.session_state.update({"invite_code": ci, "my_name": ui, "page": "dashboard"}); st.rerun()

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="refresh")
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 학습 & AI", "📋 커뮤니티", "💡 진로상담"])
        
        st.sidebar.divider()
        st.sidebar.subheader("👥 팀원 현황")
        for m in data.get('members', []):
            st.sidebar.write(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']}: {m['status']}")
        
        if st.sidebar.button("⬅️ 나가기"): st.session_state.page = 'gate'; st.rerun()

        col_main, col_ai = st.columns([1, 1])

        with col_main:
            if menu == "📚 학습 & AI":
                st.header("📚 과목 관리")
                my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
                
                with st.expander("➕ 과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data.get('subjects', {}); all_s[st.session_state.my_name] = my_subs
                        update_db(st.session_state.invite_code, "subjects", all_s); st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("과목 선택", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("파일 업로드 (PDF/TXT)", type=['pdf', 'txt'])
                    
                    if up_file:
                        st.session_state.temp_content = extract_text(up_file)
                        st.success("파일 읽기 완료!")

                    # [동작 보증 버튼 1] 일정 생성
                    if st.button("🗓️ 일정 만들기"):
                        if st.session_state.temp_content:
                            with st.spinner("AI가 분석 중..."):
                                res = model.generate_content(f"이 내용을 바탕으로 학습 일정을 짜줘: {st.session_state.temp_content[:4000]}")
                                st.session_state.ai_ans = res.text
                                st.rerun()
                        else: st.warning("파일을 먼저 올려주세요.")

                    st.divider()
                    if st.button("🚀 공부 시작"):
                        ml = data['members']
                        for m in ml:
                            if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {sel_sub} 중"
                        update_db(st.session_state.invite_code, "members", ml); st.rerun()
                    
                    # [동작 보증 버튼 2] 종료 및 퀴즈
                    if st.button("🏁 종료 & 테스트 퀴즈"):
                        ml = data['members']
                        for m in ml:
                            if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                        update_db(st.session_state.invite_code, "members", ml)
                        
                        if st.session_state.temp_content:
                            with st.spinner("퀴즈 생성 중..."):
                                res = model.generate_content(f"이 내용에서 중요한 퀴즈 3개 내줘: {st.session_state.temp_content[:4000]}")
                                st.session_state.ai_ans = res.text
                        else: st.session_state.ai_ans = "자료가 없어 퀴즈 대신 응원을 보냅니다. 고생했어!"
                        st.rerun()

            elif menu == "📋 커뮤니티":
                st.header("📋 게시판")
                with st.form("p_form"):
                    pt = st.text_input("제목"); pc = st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data.get('posts', []) or []
                        ps.append({"title": pt, "content": pc, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        update_db(st.session_state.invite_code, "posts", ps); st.rerun()
                for p in reversed(data.get('posts', [])):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 진로 상담")
                q_text = st.text_area("고민 입력")
                # [동작 보증 버튼 3] 상담
                if st.button("🔮 상담 시작"):
                    if q_text:
                        with st.spinner("상담 답변 생성 중..."):
                            res = model.generate_content(f"진로 상담가로서 답변해줘: {q_text}")
                            st.session_state.ai_ans = res.text
                            st.rerun()

        with col_ai:
            # --- 고정된 AI 답변 칸 ---
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.write(st.session_state.ai_ans)
                if st.button("결과 지우기"):
                    st.session_state.ai_ans = ""; st.rerun()
            else:
                st.info("AI의 분석 결과가 여기에 표시됩니다.")
