import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 설정 (본인의 키로 교체) ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co" 
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

# --- 2. 세션 및 상태 관리 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_subjects' not in st.session_state:
    st.session_state.my_subjects = ["기본 과목"]

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

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.subheader("AI 실시간 멀티 스터디 플랫폼")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True):
            st.session_state.page = 'create'
            st.rerun()
    with c2:
        if st.button("🔗 참여하기", use_container_width=True):
            st.session_state.page = 'join'
            st.rerun()

# [팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 새로운 팀 만들기")
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
                st.error(f"생성 실패: {e}")

# [참여하기]
elif st.session_state.page == 'join':
    st.title("🔗 팀 참여하기")
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
        else:
            st.error("코드가 올바르지 않습니다.")

# [메인 대시보드]
elif st.session_state.page == 'dashboard':
    # 5초마다 팀원 상태 업데이트
    st_autorefresh(interval=5000, key="f5")
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        data = res.data[0]
        st.title(f"🏫 {data['team_name']}")
        st.caption(f"코드: {st.session_state.invite_code} | 사용자: {st.session_state.my_name}")

        # 1. 팀원 실시간 현황
        st.subheader("👥 팀원 실시간 상태")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                status_color = "green" if "🔥" in m['status'] else "gray"
                st.markdown(f"""
                    <div style="border:1px solid #ddd; border-radius:10px; padding:10px; text-align:center; background-color:white;">
                        <b style="color:black;">{m['name']}</b><br>
                        <span style="color:{status_color}; font-size:0.8em;">{m['status']}</span>
                    </div>
                """, unsafe_allow_html=True)

        st.divider()

        # 2. 개인별 과목 관리 및 학습
        st.subheader("📚 나의 학습실")
        
        # 과목 추가 입력창
        c_add1, c_add2 = st.columns([3, 1])
        with c_add1:
            new_sub = st.text_input("새 과목 추가", placeholder="예: 데이터베이스, 알고리즘", label_visibility="collapsed")
        with c_add2:
            if st.button("➕ 추가", use_container_width=True):
                if new_sub and new_sub not in st.session_state.my_subjects:
                    st.session_state.my_subjects.append(new_sub)
                    st.rerun()

        # 과목별 탭 생성
        tabs = st.tabs(st.session_state.my_subjects)
        for i, tab in enumerate(tabs):
            s_name = st.session_state.my_subjects[i]
            with tab:
                st.write(f"📖 **{s_name}** 세션")
                up_file = st.file_uploader(f"{s_name} 자료 업로드", key=f"file_{s_name}")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"🚀 {s_name} 시작", key=f"start_{s_name}", use_container_width=True):
                        update_db_status(f"🔥 {s_name} 공부 중")
                        st.rerun()
                with col_btn2:
                    if st.button(f"🏁 {s_name} 종료/퀴즈", key=f"end_{s_name}", use_container_width=True):
                        update_db_status("✅ 대기 중")
                        if up_file:
                            with st.spinner("AI 퀴즈 생성 중..."):
                                prompt = f"{s_name}에 대한 핵심 퀴즈 3개를 내줘."
                                resp = model.generate_content(prompt)
                                st.session_state.last_quiz = resp.text
                                st.rerun()
                        else:
                            st.warning("자료를 올려주시면 퀴즈를 풀 수 있습니다!")

        # 퀴즈 결과창
        if 'last_quiz' in st.session_state:
            with st.expander("🤖 AI 학습 퀴즈 결과", expanded=True):
                st.write(st.session_state.last_quiz)
                if st.button("확인 완료"):
                    del st.session_state.last_quiz
                    st.rerun()

        st.divider()

        # 3. AI 진로 상담소
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("진로 고민을 적어주세요 (전공, 취업, 로드맵 등)")
        if st.button("🔮 AI 컨설팅 받기", use_container_width=True):
            if career_q:
                with st.spinner("컨설턴트 AI 분석 중..."):
                    prompt = f"너는 커리어 전문가야. 고민: {career_q}. 추천 직무와 학습 로드맵을 제안해줘."
                    resp = model.generate_content(prompt)
                    st.info("🤖 AI 컨설턴트의 제안")
                    st.write(resp.text)

        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.page = 'gate'
            st.rerun()
