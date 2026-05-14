import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh # requirements.txt에 추가 필수!

# --- 1. 설정 ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co"
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

@st.cache_resource
def init_connection():
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    m = genai.GenerativeModel('gemini-1.5-flash')
    return s, m

supabase, model = init_connection()

if 'page' not in st.session_state:
    st.session_state.page = 'gate'

def update_db_status(new_status):
    res = supabase.table("team").select("members").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        m_list = res.data[0]['members']
        for m in m_list:
            if m['name'] == st.session_state.my_name:
                m['status'] = new_status
        supabase.table("team").update({"members": m_list}).eq("invite_code", st.session_state.invite_code).execute()

# --- 2. 화면 로직 ---

# [게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성"):
            st.session_state.page = 'create'
            st.rerun()
    with c2:
        if st.button("🔗 참여하기"):
            st.session_state.page = 'join'
            st.rerun()

# [팀 생성]
elif st.session_state.page == 'create':
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("만들기"):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        supabase.table("team").insert({
            "invite_code": code, "team_name": t_name,
            "members": [{"name": u_name, "status": "✅ 대기"}],
            "subjects": {"기본": {}}
        }).execute()
        st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
        st.rerun()

# [참여하기]
elif st.session_state.page == 'join':
    code_in = st.text_input("코드 입력").upper()
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

# [대시보드] - 여기서 SyntaxError가 났던 부분입니다!
elif st.session_state.page == 'dashboard':
    # 5초 자동 새로고침 (실시간 현황 업데이트)
    st_autorefresh(interval=5000, key="f5")
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        data = res.data[0]
        st.title(f"🏫 {data['team_name']}")
        
        # 1. 팀원 현황 상단 표시
        st.subheader("👥 실시간 팀원 현황")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                # 공부 중일 때 색상을 다르게 표시
                color = "green" if "🔥" in m['status'] else "blue"
                st.markdown(f"""
                    <div style="border:1px solid #ddd; border-radius:10px; padding:10px; text-align:center;">
                        <b>{m['name']}</b><br><span style="color:{color};">{m['status']}</span>
                    </div>
                """, unsafe_allow_html=True)
        
        st.divider()

        # 2. 과목 및 공부 시작 버튼 (이 부분이 안 떴을 확률이 큼)
        # 데이터에 subjects가 없으면 빈 딕셔너리로 취급
        subjects = data.get('subjects', {})
        
        # 만약 과목이 아예 없다면 기본 과목 하나 추가
        if not subjects:
            subjects = {"자유공부": {}}

        st.subheader("📚 과목별 학습실")
        tabs = st.tabs(list(subjects.keys()))
        
        for i, tab in enumerate(tabs):
            s_name = list(subjects.keys())[i]
            with tab:
                st.write(f"현재 **{s_name}** 학습 세션입니다.")
                
                # 파일 업로더
                up_file = st.file_uploader(f"{s_name} 자료 업로드 (AI 퀴즈용)", key=f"f_{s_name}")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"🚀 {s_name} 공부 시작", key=f"btn_s_{s_name}"):
                        update_db_status(f"🔥 {s_name} 공부중")
                        st.success(f"{s_name} 공부를 시작했습니다!")
                        st.rerun()
                with c2:
                    if st.button(f"🏁 공부 종료 & 퀴즈", key=f"btn_e_{s_name}"):
                        update_db_status("✅ 완료")
                        if up_file:
                            with st.spinner("AI가 문제를 출제 중..."):
                                # Gemini 퀴즈 생성 로직
                                prompt = f"{s_name} 과목에 대해 공부를 마쳤습니다. 중요한 퀴즈 3개를 내주세요."
                                response = model.generate_content(prompt)
                                st.info("🤖 AI 핵심 퀴즈")
                                st.write(response.text)
                        else:
                            st.warning("자료를 업로드하면 AI 퀴즈를 풀 수 있습니다!")
        
        if st.button("🚪 로그아웃"):
            st.session_state.page = 'gate'
            st.rerun()
