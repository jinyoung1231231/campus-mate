import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader
import io

# --- 1. 서비스 연결 및 AI 초기화 (404 에러 방지 버전) ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        
        # [핵심 수정] 404 에러 차단을 위해 모델 이름을 최신 표준으로 고정 시도
        genai.configure(api_key=g_key)
        
        selected_model = None
        # 서버에서 가장 잘 인식하는 모델명 후보군
        candidates = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']
        
        for name in candidates:
            try:
                m = genai.GenerativeModel(name)
                # 테스트 호출로 404 여부 확인
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
                selected_model = m
                break
            except Exception:
                continue
        
        return s, selected_model
    except Exception as e:
        st.error(f"🚨 연결 초기화 실패: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 (데이터 유실 방지) ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'file_content' not in st.session_state: st.session_state.file_content = ""

# --- 3. 핵심 기능 함수 ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([page.extract_text() for page in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def run_ai(prompt_type, **kwargs):
    """AI를 호출하고 결과를 우측 칸에 박제하는 함수"""
    if not model:
        st.session_state.ai_ans = "🚨 AI 모델이 연결되지 않았습니다. API 키를 확인하세요."
        return
    
    with st.spinner("AI 분석 중..."):
        try:
            if prompt_type == "plan":
                p = f"성적목표:{kwargs['grade']}, 남은기간:{kwargs['days']}일. 다음 자료를 분석해 일정을 짜줘: {st.session_state.file_content[:4000]}"
            elif prompt_type == "quiz":
                p = f"다음 공부 자료에서 핵심 퀴즈 3개와 정답을 내줘: {st.session_state.file_content[:4000]}"
            elif prompt_type == "consult":
                p = f"진로 상담가로서 조언해줘: {kwargs['q']}"
            
            res = model.generate_content(p)
            st.session_state.ai_ans = res.text
        except Exception as e:
            st.session_state.ai_ans = f"❌ AI 호출 실패: {str(e)}"

# --- 4. UI 화면 구성 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀 이름")
        un = st.text_input("닉네임(생성)")
        if st.button("방 만들기"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": tn,
                "members": [{"name": un, "status": "✅ 대기", "grade": "-", "days": "-"}],
                "subjects": {un: []}, "posts": []
            }).execute()
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
        ci = st.text_input("코드 입력")
        ui = st.text_input("닉네임(참여)")
        if st.button("참여하기"):
            res = supabase.table("team").select("*").eq("invite_code", ci).execute()
            if res.data:
                d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
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

        col_main, col_ai = st.columns([1, 1])

        with col_main:
            if menu == "📚 학습 & AI 플래너":
                st.header("📚 전략 학습 플래너")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                with st.expander("과목 추가/삭제"):
                    ns = st.text_input("과목명")
                    if st.button("추가"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("자료 업로드(PDF/TXT)", type=['pdf', 'txt'])
                    if up_file:
                        st.session_state.file_content = extract_text(up_file)
                        st.success("✅ 파일 인식 완료!")

                    st.divider()
                    st.markdown("#### 🎯 목표 및 기간 설정")
                    exam_date = st.date_input("시험일 선택", value=date.today())
                    d_day = (exam_date - date.today()).days
                    grade = st.selectbox("원하는 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 맞춤 일정 생성", use_container_width=True):
                        if st.session_state.file_content and d_day >= 0:
                            # DB에 나의 목표 업데이트
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name:
                                    m['grade'] = grade; m['days'] = f"D-{d_day}"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai("plan", grade=grade, days=d_day)
                            st.rerun()
                        else: st.warning("파일을 올리고 미래의 날짜를 선택하세요.")

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
                            if st.session_state.file_content: run_ai("quiz")
                            st.rerun()

            elif menu == "👥 팀원 상세 과정":
                st.header("👥 팀원 학습 과정")
                for m in data['members']:
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님의 학습 정보"):
                        c1, c2 = st.columns(2)
                        c1.metric("목표 성적", m.get('grade', '-'))
                        c2.metric("남은 기간", m.get('days', '-'))
                        st.write(f"현재 상태: **{m['status']}**")
                        subs = data['subjects'].get(m['name'], [])
                        st.caption(f"등록 과목: {', '.join([s['name'] for s in subs]) if subs else '없음'}")

            elif menu == "📋 게시판":
                st.header("📋 팀 공유 게시판")
                with st.form("p_form", clear_on_submit=True):
                    t = st.text_input("제목"); c = st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 입력")
                if st.button("🔮 상담 시작"):
                    if q: run_ai("consult", q=q); st.rerun()

        with col_ai:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 결과 지우기"): st.session_state.ai_ans = ""; st.rerun()
            else: st.info("여기에 AI의 분석 결과가 표시됩니다.")
