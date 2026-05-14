import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# --- 1. 서비스 연결 및 AI 초기화 ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        
        selected_model = None
        for name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
            try:
                m = genai.GenerativeModel(name)
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
                selected_model = m
                break
            except: continue
        return s, selected_model
    except Exception as e:
        st.error(f"연결 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 초기화 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'invite_code' not in st.session_state: st.session_state.invite_code = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'file_content' not in st.session_state: st.session_state.file_content = ""

# --- 3. 유틸리티 함수 ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def run_ai(prompt_type, **kwargs):
    if not model:
        st.error("🤖 AI 모델 연결 실패. API 키를 확인하세요.")
        return
    with st.spinner("AI 분석 중..."):
        try:
            if prompt_type == "plan":
                p = f"성적목표:{kwargs['grade']}, 기간:{kwargs['days']}일. 자료 분석 스케줄: {st.session_state.file_content[:4000]}"
            elif prompt_type == "quiz":
                p = f"자료 기반 퀴즈 3개와 정답: {st.session_state.file_content[:4000]}"
            elif prompt_type == "consult":
                p = f"상담 답변: {kwargs['q']}"
            res = model.generate_content(p)
            st.session_state.ai_ans = res.text
            st.rerun()
        except Exception as e:
            st.error(f"AI 호출 에러: {e}")

# --- 4. 메인 UI ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀 이름")
        un = st.text_input("내 닉네임", key="create_un")
        if st.button("방 만들기"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": tn,
                "members": [{"name": un, "status": "✅ 대기", "grade": "-", "days": "-"}],
                "subjects": {un: []}, "posts": []
            }).execute()
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"})
            st.rerun()
    with c2:
        st.subheader("🔗 참여하기")
        ci = st.text_input("초대 코드")
        ui = st.text_input("내 닉네임", key="join_ui")
        if st.button("팀 입장"):
            res = supabase.table("team").select("*").eq("invite_code", ci).execute()
            if res.data:
                d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                if not any(m['name'] == ui for m in ml):
                    ml.append({"name": ui, "status": "✅ 대기", "grade": "-", "days": "-"})
                    sl[ui] = []
                    supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                st.session_state.update({"invite_code": ci, "my_name": ui, "page": "dashboard"})
                st.rerun()

elif st.session_state.page == 'dashboard':
    if not st.session_state.my_name or not st.session_state.invite_code:
        st.session_state.page = 'gate'; st.rerun()

    st_autorefresh(interval=30000, key="db_ref")
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        # [수정] 초대 코드 확인 - 클릭해야 보이도록 변경
        with st.sidebar.expander("🎫 팀 초대 코드 확인"):
            st.code(data['invite_code'], language="text")
            st.caption("친구들에게 코드를 공유하세요!")
            
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 내 학습 & AI", "👥 팀원 과목 상세", "📋 게시판", "💡 진로상담"])
        if st.sidebar.button("⬅️ 로그아웃"): 
            st.session_state.page = 'gate'; st.rerun()

        col_left, col_right = st.columns([1, 1])

        with col_left:
            if menu == "📚 내 학습 & AI":
                st.header("📚 내 공부 & AI 플랜")
                my_name = st.session_state.my_name
                my_subs = data['subjects'].get(my_name, [])
                
                with st.expander("➕ 내 과목 등록/관리"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 공부할 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("교안 업로드(PDF/TXT)", type=['pdf', 'txt'])
                    if up_file:
                        st.session_state.file_content = extract_text(up_file)
                        st.success("✅ 파일 인식 완료")

                    st.divider()
                    c_d, c_g = st.columns(2)
                    with c_d: days = st.number_input("남은 기간(일)", 1, 100, 7)
                    with c_g: grade = st.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 맞춤 일정 생성", use_container_width=True):
                        if st.session_state.file_content:
                            ml = data['members']
                            for m in ml:
                                if m['name'] == my_name:
                                    m['grade'] = grade; m['days'] = f"{days}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai("plan", grade=grade, days=days)
                        else: st.warning("파일을 먼저 업로드하세요.")

                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == my_name: m['status'] = f"🔥 {sel_sub} 중"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 퀴즈", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == my_name: m['status'] = "✅ 대기"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            if st.session_state.file_content: run_ai("quiz")
                            st.rerun()

            elif menu == "👥 팀원 과목 상세":
                st.header("👥 팀원별 학습 상세 현황")
                st.write("팀원을 클릭하여 등록된 과목 리스트를 확인하세요.")
                for m in data['members']:
                    # [수정] 팀원별 과목 정보 상세 표시
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님의 학습 정보"):
                        c1, c2 = st.columns(2)
                        c1.metric("목표 성적", m.get('grade', '-'))
                        c2.metric("남은 기간", m.get('days', '-'))
                        st.write(f"현재 상태: **{m['status']}**")
                        
                        st.divider()
                        st.write("**📚 등록된 모든 과목**")
                        f_subs = data['subjects'].get(m['name'], [])
                        if f_subs:
                            for i, s in enumerate(f_subs):
                                st.info(f"{i+1}. {s['name']}")
                        else:
                            st.caption("아직 등록된 과목이 없습니다.")

            elif menu == "📋 게시판":
                st.header("📋 팀 공유 게시판")
                with st.form("board"):
                    bt, bc = st.text_input("제목"), st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": bt, "content": bc, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 내용")
                if st.button("🔮 상담 시작"):
                    if q: run_ai("consult", q=q)

        with col_right:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 지우기"): 
                    st.session_state.ai_ans = ""; st.rerun()
            else: st.info("AI의 분석 결과가 여기에 표시됩니다.")
