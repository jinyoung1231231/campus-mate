import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 환경 설정 (본인의 키로 교체하세요) ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co" # 끝에 / 없이
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

@st.cache_resource
def init_connection():
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    m = genai.GenerativeModel('gemini-1.5-flash')
    return s, m

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"연결 오류: {e}")

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'

def update_db_status(new_status):
    try:
        res = supabase.table("team").select("members").eq("invite_code", st.session_state.invite_code).execute()
        if res.data:
            m_list = res.data[0]['members']
            for m in m_list:
                if m['name'] == st.session_state.my_name:
                    m['status'] = new_status
            supabase.table("team").update({"members": m_list}).eq("invite_code", st.session_state.invite_code).execute()
    except Exception as e:
        st.error(f"상태 업데이트 실패: {e}")

# --- 3. 화면 로직 ---

# [화면 0: 게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.subheader("AI 실시간 멀티 스터디 & 진로 컨설팅")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True):
            st.session_state.page = 'create'
            st.rerun()
    with col2 if 'col2' in locals() else c2:
        if st.button("🔗 참여하기", use_container_width=True):
            st.session_state.page = 'join'
            st.rerun()

# [화면 1: 팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 팀 만들기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("생성 완료"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            try:
                supabase.table("team").insert({
                    "invite_code": code,
                    "team_name": t_name,
                    "members": [{"name": u_name, "status": "✅ 대기"}],
                    "subjects": {}
                }).execute()
                st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
                st.rerun()
            except Exception as e:
                st.error(f"생성 실패 (RLS 확인 필요): {e}")

# [화면 2: 참여하기]
elif st.session_state.page == 'join':
    st.title("🔗 팀 참여")
    code_in = st.text_input("초대 코드 6자리").upper()
    u_name = st.text_input("내 닉네임")
    if st.button("입장"):
        res = supabase.table("team").select("*").eq("invite_code", code_in).execute()
        if res.data:
            m_list = res.data[0]['members']
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기"})
                supabase.table("team").update({"members": m_list}).eq("invite_code", code_in).execute()
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()

# [화면 3: 메인 대시보드]
elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=5000, key="f5") # 5초 자동 갱신
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        data = res.data[0]
        st.title(f"🏫 {data['team_name']}")
        st.caption(f"코드: {st.session_state.invite_code} | 사용자: {st.session_state.my_name}")

        # 1. 실시간 팀원 현황
        st.subheader("👥 팀원 현황")
        cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with cols[i % 5]:
                st.info(f"**{m['name']}**\n\n{m['status']}")

        st.divider()

        # 2. 개인별 맞춤 학습
        st.subheader("📚 오늘의 열공")
        my_task = st.text_input("지금 무엇을 공부하시나요?", placeholder="예: 경제학 원론, 파이썬 알고리즘")
        up_file = st.file_uploader("학습 자료 업로드 (AI 퀴즈용)")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 공부 시작", use_container_width=True):
                if my_task:
                    update_db_status(f"🔥 {my_task} 중")
                    st.rerun()
        with c2:
            if st.button("🏁 종료 및 AI 퀴즈", use_container_width=True):
                update_db_status("✅ 완료")
                if up_file:
                    with st.spinner("AI가 문제를 출제 중..."):
                        prompt = f"사용자가 '{my_task}'를 공부했습니다. 관련해서 아주 중요한 핵심 퀴즈 3개와 정답을 알려줘."
                        resp = model.generate_content(prompt)
                        st.session_state.quiz = resp.text
                else:
                    st.warning("자료를 올려주시면 퀴즈가 생성됩니다.")

        if 'quiz' in st.session_state:
            st.success("🤖 AI 핵심 퀴즈")
            st.write(st.session_state.quiz)

        st.divider()

        # 3. AI 진로 상담소
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("진로, 취업, 전공 고민을 적어주세요.")
        if st.button("🔮 진로 컨설팅 받기"):
            if career_q:
                with st.spinner("전문 컨설턴트 AI 분석 중..."):
                    prompt = f"너는 커리어 컨설턴트야. 사용자의 고민: {career_q}. 관련 직무 추천과 로드맵을 아주 친절하게 제안해줘."
                    resp = model.generate_content(prompt)
                    st.info("🤖 AI의 조언")
                    st.write(resp.text)

        if st.button("🚪 로그아웃"):
            st.session_state.page = 'gate'
            st.rerun()
