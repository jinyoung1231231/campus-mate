import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader
import io

# --- 1. 서비스 연결 초기화 (캐싱 적용) ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        
        # 모델 명칭 및 연결 안정성 확보
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
        st.error(f"연결 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'permanent_text' not in st.session_state: st.session_state.permanent_text = ""

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

# --- 4. UI 로직 ---

# [게이트웨이]
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

# [메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="refresh") # 실시간 갱신
    data = get_team_data(st.session_state.invite_code)
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 학습 & AI 도구", "👥 팀원 정보 열람", "📋 커뮤니티", "💡 진로상담"])
        
        st.sidebar.divider()
        st.sidebar.subheader("👥 실시간 현황")
        for m in data.get('members', []):
            st.sidebar.write(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']}: {m['status']}")
        
        if st.sidebar.button("⬅️ 나가기"): st.session_state.page = 'gate'; st.rerun()

        col_main, col_ai = st.columns([1, 1]) # 좌측 기능, 우측 AI 답변

        with col_main:
            # 1. 학습 도구 (파일 분석 & 일정 생성)
            if menu == "📚 학습 & AI 도구":
                st.header("📚 전략적 학습 플래너")
                my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
                
                with st.expander("➕ 내 과목 추가"):
                    ns = st.text_input("과목명 입력")
                    if st.button("등록"):
                        my_subs.append({"name": ns}); all_s = data.get('subjects', {}); all_s[st.session_state.my_name] = my_subs
                        update_db(st.session_state.invite_code, "subjects", all_s); st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 타겟 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("학습 자료(PDF/TXT) 업로드", type=['pdf', 'txt'])
                    
                    if up_file:
                        st.session_state.permanent_text = extract_text(up_file)
                        st.success("✅ 자료가 메모리에 저장되었습니다.")

                    st.divider()
                    c_day, c_grade = st.columns(2)
                    with c_day: days = st.number_input("학습 기간(일)", min_value=1, value=7)
                    with c_grade: grade = st.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 맞춤 일정 생성", use_container_width=True):
                        if model and st.session_state.permanent_text:
                            with st.spinner("AI 분석 중..."):
                                prompt = f"자료: {st.session_state.permanent_text[:4000]}\n목표: {grade}, 기간: {days}일\n이 목표에 맞춘 학습 플랜을 짜줘."
                                res = model.generate_content(prompt)
                                st.session_state.ai_ans = res.text
                                st.rerun()
                        else: st.warning("파일을 먼저 업로드해 주세요.")

                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {sel_sub} 중"
                            update_db(st.session_state.invite_code, "members", ml); st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 퀴즈", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            update_db(st.session_state.invite_code, "members", ml)
                            if model and st.session_state.permanent_text:
                                res = model.generate_content(f"핵심 퀴즈 3개: {st.session_state.permanent_text[:3000]}")
                                st.session_state.ai_ans = res.text
                            st.rerun()

            # 2. 다른 사람 정보 열람 (새로 추가된 기능!)
            elif menu == "👥 팀원 정보 열람":
                st.header("👥 팀원 학습 정보")
                st.write("팀원을 클릭하여 현재 어떤 과목을 공부하는지 확인하세요.")
                for m in data.get('members', []):
                    if m['name'] != st.session_state.my_name:
                        with st.expander(f"👤 {m['name']} 님의 정보"):
                            st.write(f"현재 상태: **{m['status']}**")
                            friend_subs = data.get('subjects', {}).get(m['name'], [])
                            if friend_subs:
                                st.write("등록된 과목:")
                                for fs in friend_subs:
                                    st.write(f"- {fs['name']}")
                            else: st.write("아직 등록된 과목이 없습니다.")

            # 3. 커뮤니티 게시판
            elif menu == "📋 커뮤니티":
                st.header("📋 팀 공유 게시판")
                with st.form("p_form", clear_on_submit=True):
                    pt = st.text_input("제목"); pc = st.text_area("내용")
                    if st.form_submit_button("글쓰기"):
                        ps = data.get('posts', []) or []
                        ps.append({"title": pt, "content": pc, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        update_db(st.session_state.invite_code, "posts", ps); st.rerun()
                for p in reversed(data.get('posts', [])):
                    with st.expander(f"{p['title']} - {p['author']} ({p['time']})"):
                        st.write(p['content'])

            # 4. 진로상담
            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("공민 내용")
                if st.button("🔮 상담 시작"):
                    if model and q:
                        with st.spinner("AI 상담 중..."):
                            res = model.generate_content(f"상담: {q}")
                            st.session_state.ai_ans = res.text; st.rerun()

        with col_ai:
            # --- [고정] AI 전용 답변 칸 ---
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 답변 지우기"):
                    st.session_state.ai_ans = ""; st.rerun()
            else:
                st.info("AI의 학습 플랜, 퀴즈, 상담 결과가 여기에 표시됩니다.")
