import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime, date
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
        
        found_model = None
        model_candidates = ['gemini-1.5-flash', 'gemini-1.5-pro']
        for m_name in model_candidates:
            try:
                test_model = genai.GenerativeModel(m_name)
                test_model.generate_content("hi", generation_config={"max_output_tokens": 1})
                found_model = test_model
                break
            except: continue
        return s, found_model
    except Exception as e:
        st.error(f"연결 설정 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'file_text' not in st.session_state: st.session_state.file_text = ""

# --- 3. 유틸리티 함수 ---
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

# --- 4. 화면 구성 ---
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀 이름")
        un = st.text_input("내 이름")
        if st.button("방 만들기"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({"invite_code": code, "team_name": tn, "members": [{"name": un, "status": "✅ 대기"}], "subjects": {un: []}, "posts": []}).execute()
            st.session_state.my_teams[code] = tn
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
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
        menu = st.sidebar.radio("메뉴", ["📚 학습 & AI 플래너", "📋 커뮤니티", "💡 진로상담"])
        
        st.sidebar.divider()
        st.sidebar.subheader("👥 팀원 현황")
        for m in data.get('members', []):
            st.sidebar.write(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']}: {m['status']}")
        
        if st.sidebar.button("⬅️ 나가기"): st.session_state.page = 'gate'; st.rerun()

        col_main, col_ai = st.columns([1, 1])

        with col_main:
            if menu == "📚 학습 & AI 플래너":
                st.header("📚 시험 D-Day 기반 플래너")
                my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
                
                with st.expander("➕ 과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data.get('subjects', {}); all_s[st.session_state.my_name] = my_subs
                        update_db(st.session_state.invite_code, "subjects", all_s); st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("과목 선택", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("강의자료/계획서 업로드 (PDF/TXT)", type=['pdf', 'txt'])
                    
                    if up_file:
                        st.session_state.file_text = extract_text(up_file)
                        st.success("✅ 학습 자료 로드 완료!")

                    # --- [추가] D-Day 계산 기능 ---
                    st.divider()
                    st.markdown("#### 📅 시험 일정 설정")
                    exam_date = st.date_input("시험일(목표일)을 선택하세요", value=date.today())
                    
                    # 남은 일수 계산
                    d_day = (exam_date - date.today()).days
                    
                    if d_day < 0:
                        st.error("이미 지난 날짜입니다. 미래의 날짜를 선택해주세요.")
                    else:
                        st.info(f"📍 오늘부터 시험일까지 **{d_day}일** 남았습니다.")
                        
                        if st.button("🪄 남은 기간 맞춤 일정 생성"):
                            if model and st.session_state.file_text:
                                with st.spinner(f"{d_day}일 완성 플랜 짜는 중..."):
                                    prompt = f"""
                                    사용자는 오늘부터 {d_day}일 후에 시험을 봅니다.
                                    제공된 학습 자료를 분석하여 남은 {d_day}일 동안의 '역산 스케줄'을 짜주세요.
                                    - 전체 분량을 고려한 일일 학습량 제안
                                    - 마지막 20% 기간은 총정리 기간으로 배정
                                    자료 내용: {st.session_state.file_text[:5000]}
                                    """
                                    try:
                                        res = model.generate_content(prompt)
                                        st.session_state.ai_ans = res.text
                                        st.rerun()
                                    except Exception as e: st.error(f"AI 호출 실패: {e}")
                            else: st.warning("분석할 강의자료(파일)를 먼저 올려주세요.")

                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작"):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {sel_sub} 중"
                            update_db(st.session_state.invite_code, "members", ml); st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 테스트"):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            update_db(st.session_state.invite_code, "members", ml)
                            if model and st.session_state.file_text:
                                with st.spinner("복습 퀴즈 생성 중..."):
                                    res = model.generate_content(f"이 내용에서 중요한 퀴즈 3개 내줘: {st.session_state.file_text[:4000]}")
                                    st.session_state.ai_ans = res.text
                            st.rerun()

            elif menu == "📋 커뮤니티":
                st.header("📋 팀 게시판")
                with st.form("p_form", clear_on_submit=True):
                    pt = st.text_input("제목"); pc = st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data.get('posts', []) or []
                        ps.append({"title": pt, "content": pc, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        update_db(st.session_state.invite_code, "posts", ps); st.rerun()
                for p in reversed(data.get('posts', []) or []):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q_text = st.text_area("고민 입력")
                if st.button("🔮 상담 시작"):
                    if model and q_text:
                        with st.spinner("분석 중..."):
                            res = model.generate_content(f"상담 답변: {q_text}")
                            st.session_state.ai_ans = res.text
                            st.rerun()

        with col_ai:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("결과 지우기"):
                    st.session_state.ai_ans = ""; st.rerun()
            else: st.info("AI의 플래닝 결과가 여기에 표시됩니다.")
