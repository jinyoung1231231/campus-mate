import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader
import io

# --- 1. 초기 설정 및 AI 연결 (에러 방지 로직 포함) ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        
        # 모델 명칭 유연성 확보 (404 에러 방지)
        m = None
        for name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
            try:
                temp = genai.GenerativeModel(name)
                temp.generate_content("hi", generation_config={"max_output_tokens": 1})
                m = temp
                break
            except: continue
        return s, m
    except Exception as e:
        st.error(f"연결 설정 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'file_content' not in st.session_state: st.session_state.file_content = ""

# --- 3. AI 실행 전용 함수 ---
def run_ai_task(prompt_type, **kwargs):
    if not model:
        st.session_state.ai_ans = "🚨 AI 모델 연결 실패"
        return
    with st.spinner("AI가 분석 중입니다..."):
        try:
            if prompt_type == "plan":
                p = f"목표:{kwargs['grade']}, 기간:{kwargs['days']}일. 자료 요약 및 일정표 생성: {st.session_state.file_content[:4000]}"
            elif prompt_type == "quiz":
                p = f"다음 내용에서 핵심 퀴즈 3개와 정답: {st.session_state.file_content[:4000]}"
            elif prompt_type == "consult":
                p = f"고민 상담: {kwargs['question']}"
            
            response = model.generate_content(p)
            st.session_state.ai_ans = response.text
        except Exception as e:
            st.session_state.ai_ans = f"❌ AI 작동 오류: {str(e)}"

# --- 4. 데이터 보조 함수 ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([page.extract_text() for page in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

# --- 5. UI 화면 구성 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀명"); un = st.text_input("닉네임(생성)")
        if st.button("생성"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            # [수정] members 구조에 학습 상세 정보(target_grade, target_days) 추가
            supabase.table("team").insert({
                "invite_code": code, "team_name": tn, 
                "members": [{"name": un, "status": "✅ 대기", "grade": "-", "days": "-"}], 
                "subjects": {un: []}, "posts": []
            }).execute()
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
        ci = st.text_input("코드"); ui = st.text_input("닉네임(참여)")
        if st.button("참여"):
            data = supabase.table("team").select("*").eq("invite_code", ci).execute().data
            if data:
                d = data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                if not any(m['name'] == ui for m in ml):
                    ml.append({"name": ui, "status": "✅ 대기", "grade": "-", "days": "-"})
                    sl[ui] = []
                    supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                st.session_state.update({"invite_code": ci, "my_name": ui, "page": "dashboard"}); st.rerun()

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="db_ref")
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 학습 & AI 플래너", "👥 팀원 상세 과정", "📋 게시판", "💡 진로상담"])
        
        if st.sidebar.button("⬅️ 나가기"): st.session_state.page = 'gate'; st.rerun()

        col_left, col_right = st.columns([1, 1])

        with col_left:
            if menu == "📚 학습 & AI 플래너":
                st.header("📚 전략 학습 플래너")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                with st.expander("내 과목 관리"):
                    ns = st.text_input("추가할 과목명")
                    if st.button("추가"):
                        my_subs.append({"name": ns})
                        s_all = data['subjects']; s_all[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": s_all}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("공부할 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("자료 업로드(PDF/TXT)", type=['pdf', 'txt'])
                    if up_file:
                        st.session_state.file_content = extract_text(up_file)
                        st.success("자료 인식 완료")

                    c_d, c_g = st.columns(2)
                    d_val = c_d.number_input("목표 기간(일)", 1, 100, 7)
                    g_val = c_g.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 일정 및 전략 생성", use_container_width=True):
                        if st.session_state.file_content:
                            run_ai_task("plan", grade=g_val, days=d_val)
                            # [핵심] 내 학습 목표를 DB에도 업데이트하여 팀원들이 보게 함
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name:
                                    m['grade'] = g_val; m['days'] = f"{d_val}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
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
                        if st.button("✅ 휴식/종료", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            if st.session_state.file_content: run_ai_task("quiz")
                            st.rerun()

            elif menu == "👥 팀원 상세 과정":
                st.header("👥 팀원 학습 과정 모니터링")
                st.write("팀원들이 어떤 전략으로 공부하고 있는지 확인하세요.")
                for m in data['members']:
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님의 학습 정보"):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("현재 상태", m['status'])
                        c2.metric("목표 성적", m.get('grade', '-'))
                        c3.metric("학습 기간", m.get('days', '-'))
                        
                        st.write("**등록된 과목 리스트:**")
                        friend_subs = data['subjects'].get(m['name'], [])
                        if friend_subs:
                            st.caption(", ".join([s['name'] for s in friend_subs]))
                        else: st.caption("등록된 과목 없음")

            elif menu == "📋 게시판":
                st.header("📋 팀 공유 게시판")
                with st.form("p_f"):
                    t, c = st.text_input("제목"), st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']} ({p['time']})"):
                        st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 입력")
                if st.button("🔮 상담 시작", use_container_width=True):
                    if q: run_ai_task("consult", question=q); st.rerun()

        with col_right:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.info(st.session_state.ai_ans)
                if st.button("🧹 지우기"): st.session_state.ai_ans = ""; st.rerun()
            else: st.write("여기에 AI의 분석 결과가 표시됩니다.")
