import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader
import io

# --- 1. 초기 설정 및 AI 연결 ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        # 최신 모델 고정
        return s, genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"연결 설정 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 초기화 (작동 보장의 핵심) ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'file_content' not in st.session_state: st.session_state.file_content = ""

# --- 3. AI 실행 전용 함수 (Callback) ---
def run_ai_task(prompt_type, **kwargs):
    """버튼 클릭 시 AI를 즉시 호출하고 세션에 저장하는 전용 함수"""
    if not model:
        st.session_state.ai_ans = "🚨 AI 모델이 연결되지 않았습니다."
        return

    with st.spinner("AI가 응답을 생성 중입니다..."):
        try:
            if prompt_type == "plan":
                p = f"목표성적:{kwargs['grade']}, 기간:{kwargs['days']}일. 다음 자료를 분석해 일정을 짜줘: {st.session_state.file_content[:4000]}"
            elif prompt_type == "quiz":
                p = f"다음 자료에서 핵심 퀴즈 3개와 정답을 내줘: {st.session_state.file_content[:4000]}"
            elif prompt_type == "consult":
                p = f"커리어 상담가로서 다음 고민에 조언해줘: {kwargs['question']}"
            
            response = model.generate_content(p)
            st.session_state.ai_ans = response.text
        except Exception as e:
            st.session_state.ai_ans = f"❌ AI 호출 중 에러 발생: {str(e)}"

# --- 4. 데이터 보조 함수 ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([page.extract_text() for page in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def get_db_data():
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    return res.data[0] if res.data else None

# --- 5. UI 화면 구성 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀명"); un = st.text_input("닉네임(생성)")
        if st.button("생성"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({"invite_code": code, "team_name": tn, "members": [{"name": un, "status": "✅ 대기"}], "subjects": {un: []}, "posts": []}).execute()
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
        ci = st.text_input("코드"); ui = st.text_input("닉네임(참여)")
        if st.button("참여"):
            data = supabase.table("team").select("*").eq("invite_code", ci).execute().data
            if data:
                d = data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                if not any(m['name'] == ui for m in ml):
                    ml.append({"name": ui, "status": "✅ 대기"}); sl[ui] = []
                    supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                st.session_state.update({"invite_code": ci, "my_name": ui, "page": "dashboard"}); st.rerun()

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="db_ref")
    data = get_db_data()
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 학습 & AI 플래너", "👥 팀원 정보", "📋 게시판", "💡 진로상담"])
        
        # 팀원 현황 사이드바
        st.sidebar.divider()
        for m in data['members']:
            st.sidebar.write(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']}: {m['status']}")
        
        if st.sidebar.button("⬅️ 나가기"): st.session_state.page = 'gate'; st.rerun()

        col_left, col_right = st.columns([1, 1])

        with col_left:
            # 1. 학습 & AI 도구
            if menu == "📚 학습 & AI 플래너":
                st.header("📚 전략 플래너")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                with st.expander("과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("추가"):
                        my_subs.append({"name": ns})
                        s_all = data['subjects']; s_all[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": s_all}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("과목 선택", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("자료 업로드(PDF/TXT)", type=['pdf', 'txt'])
                    if up_file:
                        st.session_state.file_content = extract_text(up_file)
                        st.success("자료 로드 완료")

                    st.divider()
                    d_val = st.number_input("학습 기간(일)", 1, 100, 7)
                    g_val = st.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 일정 만들기", use_container_width=True):
                        if st.session_state.file_content:
                            run_ai_task("plan", grade=g_val, days=d_val)
                            st.rerun()
                        else: st.warning("파일을 먼저 올려주세요.")

                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {sel_sub} 중"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 퀴즈", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            if st.session_state.file_content:
                                run_ai_task("quiz")
                            st.rerun()

            # 2. 팀원 정보 열람
            elif menu == "👥 팀원 정보":
                st.header("👥 팀원 학습 정보")
                for m in data['members']:
                    with st.expander(f"👤 {m['name']} ({m['status']})"):
                        subs = data['subjects'].get(m['name'], [])
                        if subs:
                            for s in subs: st.write(f"- {s['name']}")
                        else: st.write("등록 과목 없음")

            # 3. 게시판
            elif menu == "📋 게시판":
                st.header("📋 팀 게시판")
                with st.form("post_form"):
                    t = st.text_input("제목"); c = st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            # 4. 진로상담
            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민을 적어주세요")
                if st.button("🔮 상담 시작", use_container_width=True):
                    if q:
                        run_ai_task("consult", question=q)
                        st.rerun()

        with col_right:
            # --- [불변] AI 전용 답변 칸 ---
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.info(st.session_state.ai_ans)
                if st.button("🧹 결과 지우기"):
                    st.session_state.ai_ans = ""
                    st.rerun()
            else:
                st.write("AI의 일정, 퀴즈, 상담 결과가 여기에 표시됩니다.")
