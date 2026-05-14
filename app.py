import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# --- 1. 서비스 연결 및 AI 초기화 (404 완벽 대응) ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        genai.configure(api_key=g_key)
        
        # [해결] 404 에러 방지를 위한 자동 모델 탐색
        for m_name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
            try:
                m = genai.GenerativeModel(m_name)
                m.generate_content("ping", generation_config={"max_output_tokens": 1})
                return s, m
            except: continue
        return s, None
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

# --- 3. 핵심 유틸리티 ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def run_ai(prompt_type, **kwargs):
    if not model:
        st.error("AI 모델 연결에 실패했습니다. API 키를 확인하세요.")
        return
    with st.spinner("AI 분석 중..."):
        try:
            if prompt_type == "plan":
                p = f"목표:{kwargs['grade']}, 기간:{kwargs['days']}일. 자료 분석 일정 생성: {st.session_state.file_content[:3000]}"
            elif prompt_type == "quiz":
                p = f"자료 기반 퀴즈 3개와 정답: {st.session_state.file_content[:3000]}"
            elif prompt_type == "consult":
                p = f"상담: {kwargs['q']}"
            res = model.generate_content(p)
            st.session_state.ai_ans = res.text
            st.rerun()
        except Exception as e:
            st.error(f"AI 호출 오류 (404/지원안됨): {e}")

# --- 4. 화면 로직 ---

# [게이트 페이지: 다중 팀 관리 기능]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.markdown("### 닉네임을 입력하여 소속된 팀 목록을 확인하세요.")
    
    un = st.text_input("사용자 닉네임 입력")
    
    if un:
        # 사용자가 포함된 모든 팀 리스트 불러오기
        all_teams = supabase.table("team").select("*").execute().data
        my_team_list = [t for t in all_teams if any(m['name'] == un for m in t['members'])]
        
        if my_team_list:
            st.subheader("📋 내 팀 목록")
            for t in my_team_list:
                if st.button(f"🏠 {t['team_name']} 입장 (코드: {t['invite_code']})", key=f"join_{t['invite_code']}"):
                    st.session_state.update({"invite_code": t['invite_code'], "my_name": un, "page": "dashboard"})
                    st.rerun()
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🆕 새 팀 생성")
            tn = st.text_input("새 팀 이름")
            if st.button("방 만들기"):
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table("team").insert({
                    "invite_code": code, "team_name": tn,
                    "members": [{"name": un, "status": "✅ 대기", "grade": "-", "days": "-"}],
                    "subjects": {un: []}, "posts": []
                }).execute()
                st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
        with c2:
            st.subheader("🔗 새 코드 입장")
            ci = st.text_input("초대 코드")
            if st.button("참여하기"):
                res = supabase.table("team").select("*").eq("invite_code", ci).execute()
                if res.data:
                    d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                    if not any(m['name'] == un for m in ml):
                        ml.append({"name": un, "status": "✅ 대기", "grade": "-", "days": "-"})
                        sl[un] = []
                        supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                    st.session_state.update({"invite_code": ci, "my_name": un, "page": "dashboard"}); st.rerun()

# [대시보드 페이지]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="db_ref")
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        with st.sidebar.expander("🎫 초대코드 확인"):
            st.code(data['invite_code'])
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 내 학습 & AI", "👥 팀원 과목상세", "📋 게시판", "💡 상담"])
        
        if st.sidebar.button("⬅️ 다른 팀으로 이동"):
            st.session_state.update({"invite_code": "", "page": "gate", "ai_ans": ""}); st.rerun()

        col_l, col_r = st.columns([1, 1])
        with col_l:
            if menu == "📚 내 학습 & AI":
                st.header("📚 내 공부 관리")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                with st.expander("➕ 과목 등록"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                if my_subs:
                    sel_sub = st.selectbox("과목 선택", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("자료 업로드", type=['pdf', 'txt'])
                    if up_file: st.session_state.file_content = extract_text(up_file); st.success("인식 완료")
                    
                    c_d, c_g = st.columns(2)
                    days = c_d.number_input("남은 기간", 1, 100, 7)
                    grade = c_g.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 일정 생성"):
                        if st.session_state.file_content:
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['grade'] = grade; m['days'] = f"{days}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai("plan", grade=grade, days=days)

                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작"):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {sel_sub} 중"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 퀴즈"):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            if st.session_state.file_content: run_ai("quiz")

            elif menu == "👥 팀원 과목상세":
                st.header("👥 팀원별 상세 현황")
                for m in data['members']:
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님"):
                        st.write(f"상태: {m['status']} | 목표: {m['grade']} | 남은일: {m['days']}")
                        st.write("**📚 등록 과목:**")
                        f_subs = data['subjects'].get(m['name'], [])
                        if f_subs:
                            for s in f_subs: st.info(s['name'])

            elif menu == "📋 게시판":
                st.header("📋 팀 게시판")
                with st.form("b_form"):
                    t, c = st.text_input("제목"), st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 상담":
                st.header("💡 AI 상담")
                q = st.text_area("고민 입력")
                if st.button("🔮 상담 시작"): run_ai("consult", q=q)

        with col_r:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 지우기"): st.session_state.ai_ans = ""; st.rerun()
