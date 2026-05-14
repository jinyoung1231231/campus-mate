import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# --- 1. 서비스 연결 및 AI 자가 복구 로직 (404 완벽 대응) ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        s = create_client(s_url, s_key)
        
        # 구글 AI 설정
        genai.configure(api_key=g_key)
        
        # [해결] 작동하는 모델 경로를 찾을 때까지 3단계 시도
        candidates = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']
        working_model = None
        
        for name in candidates:
            try:
                m = genai.GenerativeModel(name)
                # 테스트 호출로 응답 확인 (404 체크)
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
                working_model = m
                break
            except:
                continue
        
        return s, working_model
    except Exception as e:
        st.error(f"🚨 시스템 초기 설정 오류: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 (유실 방지) ---
for key in ['page', 'my_name', 'invite_code', 'ai_ans', 'file_content']:
    if key not in st.session_state:
        st.session_state[key] = "gate" if key == 'page' else ""

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
        st.error("🤖 AI 모델이 연결되지 않았습니다. API 키를 확인하세요.")
        return
    with st.spinner("AI가 분석 중입니다..."):
        try:
            if prompt_type == "plan":
                p = f"목표:{kwargs['grade']}, 기간:{kwargs['days']}일. 아래 자료를 보고 학습 일정을 짜줘:\n{st.session_state.file_content[:3500]}"
            elif prompt_type == "quiz":
                p = f"아래 자료에서 핵심 퀴즈 3개와 정답을 생성해줘:\n{st.session_state.file_content[:3500]}"
            elif prompt_type == "consult":
                p = f"상담 답변: {kwargs['q']}"
            
            res = model.generate_content(p)
            st.session_state.ai_ans = res.text
            st.rerun()
        except Exception as e:
            st.error(f"❌ AI 호출 오류: {e}")

# --- 4. 화면 로직 구성 ---

# [게이트: 다중 팀 관리 및 로그인]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.markdown("#### 닉네임을 입력해 참여 중인 팀을 확인하거나 새 팀을 만드세요.")
    
    un = st.text_input("사용자 닉네임 입력 (로그인)")
    
    if un:
        # DB에서 본인이 포함된 팀 목록 조회
        try:
            all_teams = supabase.table("team").select("*").execute().data
            my_teams = [t for t in all_teams if any(m['name'] == un for m in t['members'])]
            
            if my_teams:
                st.subheader("📋 참여 중인 팀 목록")
                for t in my_teams:
                    if st.button(f"🏠 {t['team_name']} 입장", key=f"t_{t['invite_code']}"):
                        st.session_state.update({"invite_code": t['invite_code'], "my_name": un, "page": "dashboard"})
                        st.rerun()
            else:
                st.info("소속된 팀이 없습니다. 아래에서 팀을 생성하거나 코드를 입력하세요.")
        except:
            st.warning("데이터 연결 중...")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🆕 새 팀 만들기")
            tn = st.text_input("팀 이름 설정")
            if st.button("팀 생성"):
                if tn and un:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    supabase.table("team").insert({
                        "invite_code": code, "team_name": tn,
                        "members": [{"name": un, "status": "✅ 대기", "grade": "-", "days": "-"}],
                        "subjects": {un: []}, "posts": []
                    }).execute()
                    st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"})
                    st.rerun()
        with c2:
            st.subheader("🔗 초대 코드로 입장")
            ci = st.text_input("코드 입력")
            if st.button("참여하기"):
                res = supabase.table("team").select("*").eq("invite_code", ci).execute()
                if res.data:
                    d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                    if not any(m['name'] == un for m in ml):
                        ml.append({"name": un, "status": "✅ 대기", "grade": "-", "days": "-"})
                        sl[un] = []
                        supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                    st.session_state.update({"invite_code": ci, "my_name": un, "page": "dashboard"})
                    st.rerun()

# [대시보드: 학습 관리 및 팀원 현황]
elif st.session_state.page == 'dashboard':
    if not st.session_state.invite_code: 
        st.session_state.page = 'gate'; st.rerun()

    st_autorefresh(interval=30000, key="db_ref")
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        # [기능] 초대코드 숨김/표시
        with st.sidebar.expander("🎫 초대코드 확인"):
            st.code(data['invite_code'])
        
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 내 학습 & AI", "👥 팀원별 과목 정보", "📋 게시판", "💡 상담"])
        
        if st.sidebar.button("⬅️ 다른 팀으로 이동"):
            st.session_state.update({"invite_code": "", "page": "gate", "ai_ans": ""}); st.rerun()

        col_l, col_r = st.columns([1, 1])
        with col_l:
            if menu == "📚 내 학습 & AI":
                st.header("📚 내 학습 전략")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                with st.expander("➕ 내 과목 관리"):
                    ns = st.text_input("새 과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 타겟 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("교안 업로드", type=['pdf', 'txt'])
                    if up_file: st.session_state.file_content = extract_text(up_file); st.success("파일 인식 완료")
                    
                    c_d, c_g = st.columns(2)
                    days = c_d.number_input("남은 기간(일)", 1, 100, 7)
                    grade = c_g.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 맞춤 일정 생성", use_container_width=True):
                        if st.session_state.file_content:
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['grade'] = grade; m['days'] = f"{days}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai("plan", grade=grade, days=days)

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

            # [기능] 팀원별 상세 과목 정보 열람
            elif menu == "👥 팀원별 과목 정보":
                st.header("👥 팀원별 상세 학습 현황")
                for m in data['members']:
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님의 학습 정보"):
                        st.write(f"상태: **{m['status']}**")
                        st.write(f"🎯 목표: **{m.get('grade', '-')}** | ⏳ 기간: **{m.get('days', '-')}**")
                        st.divider()
                        st.write("**📚 등록된 모든 과목**")
                        f_subs = data['subjects'].get(m['name'], [])
                        if f_subs:
                            for s in f_subs: st.info(f"📘 {s['name']}")
                        else: st.caption("등록된 과목이 없습니다.")

            elif menu == "📋 게시판":
                st.header("📋 팀 공유 게시판")
                with st.form("b_form"):
                    bt, bc = st.text_input("제목"), st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": bt, "content": bc, "author": st.session_state.my_name})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 내용을 입력하세요.")
                if st.button("🔮 상담 시작"): run_ai("consult", q=q)

        with col_r:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 지우기"): st.session_state.ai_ans = ""; st.rerun()
