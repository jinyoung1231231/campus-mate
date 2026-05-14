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
        st.error(f"연결 설정 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 초기화 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'permanent_text' not in st.session_state: st.session_state.permanent_text = ""

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

# --- 4. 메인 UI ---
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀 이름", key="tn_final")
        un = st.text_input("내 이름", key="un_final")
        if st.button("방 만들기"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({"invite_code": code, "team_name": tn, "members": [{"name": un, "status": "✅ 대기"}], "subjects": {un: []}, "posts": []}).execute()
            st.session_state.my_teams[code] = tn
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 참여")
        ci = st.text_input("코드 입력", key="ci_final")
        ui = st.text_input("내 이름 ", key="ui_final")
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
                st.header("📚 전략적 학습 플래너")
                my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
                
                with st.expander("➕ 과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns}); all_s = data.get('subjects', {}); all_s[st.session_state.my_name] = my_subs
                        update_db(st.session_state.invite_code, "subjects", all_s); st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 타겟 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("학습 자료 업로드", type=['pdf', 'txt'])
                    
                    if up_file:
                        st.session_state.permanent_text = extract_text(up_file)
                        st.success("✅ 자료 분석 완료!")

                    st.divider()
                    st.markdown("#### 🎯 학습 목표 설정")
                    
                    # [추가] 목표 성적 및 기간 선택
                    c_day, c_grade = st.columns(2)
                    with c_day:
                        split_days = st.number_input("학습 기간(일)", min_value=1, value=7)
                    with c_grade:
                        target_grade = st.selectbox("목표 성적", ["A+ (완벽 암기 및 심화)", "B+ (핵심 위주)", "Pass (중요 포인트만)"])
                    
                    if st.button("🪄 AI 맞춤 전략 일정 생성", use_container_width=True):
                        if model and st.session_state.permanent_text:
                            with st.spinner(f"{target_grade} 목표로 일정 생성 중..."):
                                prompt = f"""
                                자료 내용: {st.session_state.permanent_text[:5000]}
                                목표: {target_grade} 성적 받기
                                기간: {split_days}일
                                요구사항: 위 성적 목표에 맞춰서 학습 강도를 조절한 {split_days}일 스케줄을 짜줘. 
                                A+라면 지엽적인 부분까지, Pass라면 핵심 키워드 위주로 강조해줘.
                                """
                                try:
                                    res = model.generate_content(prompt)
                                    st.session_state.ai_ans = res.text
                                    st.rerun()
                                except Exception as e: st.error(f"에러: {e}")
                        else: st.warning("파일을 먼저 업로드해주세요.")

                    st.divider()
                    # 공부 시작/종료 로직은 동일
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
                                res = model.generate_content(f"핵심 퀴즈 3개: {st.session_state.permanent_text[:4000]}")
                                st.session_state.ai_ans = res.text
                            st.rerun()

            # (게시판/상담 기능 유지)
            elif menu == "📋 커뮤니티":
                st.header("📋 팀 게시판")
                with st.form("p_form_f", clear_on_submit=True):
                    pt = st.text_input("제목"); pc = st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data.get('posts', []) or []
                        ps.append({"title": pt, "content": pc, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        update_db(st.session_state.invite_code, "posts", ps); st.rerun()
                for p in reversed(data.get('posts', []) or []):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 입력")
                if st.button("🔮 상담 시작"):
                    if model and q:
                        res = model.generate_content(f"상담 답변: {q}")
                        st.session_state.ai_ans = res.text; st.rerun()

        with col_ai:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("결과 지우기"): st.session_state.ai_ans = ""; st.rerun()
            else: st.info("AI의 전략적 답변이 표시됩니다.")
