import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# --- 1. DB 연결 (AI 캐싱 완전 제거) ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 2. 세션 상태 관리 ---
for key in ['page', 'my_name', 'invite_code', 'ai_ans', 'file_content']:
    if key not in st.session_state:
        st.session_state[key] = "gate" if key == 'page' else ""

# --- 3. 유틸리티 및 핵심 AI 로직 (ListModels 적용) ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def run_ai(prompt_type, **kwargs):
    with st.spinner("AI가 분석 중입니다..."):
        try:
            # 1. 프롬프트 세팅
            if prompt_type == "plan":
                p = f"목표:{kwargs['grade']}, 기간:{kwargs['days']}일. 아래 자료 분석 후 일정 짜줘:\n{st.session_state.file_content[:3500]}"
            elif prompt_type == "quiz":
                p = f"아래 자료에서 핵심 퀴즈 3개와 정답 내줘:\n{st.session_state.file_content[:3500]}"
            elif prompt_type == "consult":
                p = f"상담 답변해줘: {kwargs['q']}"
            
            # 2. API 키 등록
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            # 3. [핵심] 서버에 현재 사용 가능한 모델 리스트를 직접 물어봄 (404 완벽 차단)
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            if not available_models:
                st.error("❌ 현재 API 키로 사용할 수 있는 텍스트 모델이 없습니다.")
                return
            
            # 우선순위: 1.5-flash -> pro -> 리스트의 첫 번째 모델
            target_model = available_models[0]
            for m_name in available_models:
                if '1.5-flash' in m_name:
                    target_model = m_name
                    break
                elif 'pro' in m_name and 'vision' not in m_name:
                    target_model = m_name
            
            # 4. 서버가 알려준 정확한 이름으로 모델 실행
            m = genai.GenerativeModel(target_model)
            res = m.generate_content(p)
            st.session_state.ai_ans = res.text
            st.rerun() # 성공 시 새로고침
                
        except Exception as e:
            st.error(f"❌ AI 오류: {e}")

# --- 4. 화면 구성 ---

# [게이트 페이지: 로그인 및 다중 팀]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.markdown("#### 닉네임을 입력해 내 팀을 확인하거나 새로 만드세요.")
    
    un = st.text_input("사용자 닉네임 (로그인)")
    
    if un:
        # 내 소속 팀 찾기
        try:
            all_teams = supabase.table("team").select("*").execute().data
            my_teams = [t for t in all_teams if any(m['name'] == un for m in t['members'])]
            
            if my_teams:
                st.subheader("📋 내 팀 목록")
                for t in my_teams:
                    if st.button(f"🏠 {t['team_name']} 입장", key=f"t_{t['invite_code']}"):
                        st.session_state.update({"invite_code": t['invite_code'], "my_name": un, "page": "dashboard"})
                        st.rerun()
            else:
                st.info("가입된 팀이 없습니다. 아래에서 만들거나 입장하세요.")
        except:
            st.warning("데이터베이스 연결 중...")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🆕 새 팀 만들기")
            tn = st.text_input("새 팀 이름")
            if st.button("방 만들기"):
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
            ci = st.text_input("초대 코드")
            if st.button("팀 입장"):
                res = supabase.table("team").select("*").eq("invite_code", ci).execute()
                if res.data:
                    d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                    if not any(m['name'] == un for m in ml):
                        ml.append({"name": un, "status": "✅ 대기", "grade": "-", "days": "-"})
                        sl[un] = []
                        supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                    st.session_state.update({"invite_code": ci, "my_name": un, "page": "dashboard"})
                    st.rerun()

# [대시보드 페이지]
elif st.session_state.page == 'dashboard':
    if not st.session_state.invite_code: 
        st.session_state.page = 'gate'; st.rerun()

    st_autorefresh(interval=30000, key="db_ref")
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        with st.sidebar.expander("🎫 초대코드 확인 (클릭)"):
            st.code(data['invite_code'])
        
        st.sidebar.title(f"🏫 {data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["📚 내 학습 & AI", "👥 팀원 상세 과목", "📋 게시판", "💡 상담"])
        
        if st.sidebar.button("⬅️ 다른 팀으로 이동"):
            st.session_state.update({"invite_code": "", "page": "gate", "ai_ans": ""}); st.rerun()

        col_l, col_r = st.columns([1, 1])
        with col_l:
            if menu == "📚 내 학습 & AI":
                st.header("📚 내 공부 & AI 플랜")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                with st.expander("➕ 새 과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 공부할 과목", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("자료 업로드", type=['pdf', 'txt'])
                    if up_file: st.session_state.file_content = extract_text(up_file); st.success("파일 업로드 완료")
                    
                    c_d, c_g = st.columns(2)
                    days = c_d.number_input("남은 기간", 1, 100, 7)
                    grade = c_g.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 일정 생성 (서버 자동탐색)"):
                        if st.session_state.file_content:
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['grade'] = grade; m['days'] = f"{days}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai("plan", grade=grade, days=days)
                        else: st.warning("파일을 먼저 올려주세요.")

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
                        if st.button("🏁 종료 & 퀴즈 생성"):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            if st.session_state.file_content: run_ai("quiz")

            elif menu == "👥 팀원 상세 과목":
                st.header("👥 팀원별 학습 현황")
                for m in data['members']:
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님"):
                        st.write(f"상태: {m['status']} | 목표: {m['grade']} | 남은일: {m['days']}")
                        st.write("**📚 등록된 모든 과목**")
                        f_subs = data['subjects'].get(m['name'], [])
                        if f_subs:
                            for s in f_subs: st.info(s['name'])
                        else: st.caption("아직 과목을 등록하지 않았습니다.")

            elif menu == "📋 게시판":
                st.header("📋 팀 공유 게시판")
                with st.form("b_form"):
                    t, c = st.text_input("제목"), st.text_area("내용")
                    if st.form_submit_button("글 등록"):
                        ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 입력")
                if st.button("🔮 상담 시작"): run_ai("consult", q=q)

        with col_r:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 기록 지우기"): st.session_state.ai_ans = ""; st.rerun()
            else: st.info("AI의 답변이 여기에 표시됩니다.")
