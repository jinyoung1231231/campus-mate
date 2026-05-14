import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string

# --- 1. 설정 (본인의 키를 입력하세요) ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co" # 끝에 / 없이
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

# 서비스 연결
@st.cache_resource
def init_connection():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    return supabase, model

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"연결 오류: {e}")

# --- 2. 상태 관리 함수 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'

def update_db_status(new_status):
    try:
        res = supabase.table("team").select("members").eq("invite_code", st.session_state.invite_code).execute()
        if res.data:
            members = res.data[0]['members']
            for m in members:
                if m['name'] == st.session_state.my_name:
                    m['status'] = new_status
            supabase.table("team").update({"members": members}).eq("invite_code", st.session_state.invite_code).execute()
    except Exception as e:
        st.error(f"상태 업데이트 실패: {e}")

# --- 3. 화면 로직 ---

# [화면 0: 게이트웨이]
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.subheader("AI 실시간 멀티 스터디")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 팀 만들기", use_container_width=True):
            st.session_state.page = 'create'
            st.rerun()
    with col2:
        if st.button("🔗 참여하기", use_container_width=True):
            st.session_state.page = 'join'
            st.rerun()

# [화면 1: 팀 생성]
elif st.session_state.page == 'create':
    st.title("🆕 팀 생성하기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    subjects_in = st.text_input("과목들 (쉼표로 구분)", "경제학, 수학")
    
    if st.button("생성 완료"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            sub_list = [s.strip() for s in subjects_in.split(",") if s.strip()]
            sub_dict = {s: {"files": []} for s in sub_list}
            
            try:
                supabase.table("team").insert({
                    "invite_code": code,
                    "team_name": t_name,
                    "members": [{"name": u_name, "status": "✅ 대기"}],
                    "subjects": sub_dict
                }).execute()
                
                st.session_state.update({
                    "invite_code": code,
                    "my_name": u_name,
                    "page": "dashboard"
                })
                st.rerun()
            except Exception as e:
                st.error(f"DB 저장 실패: {e}")
        else:
            st.warning("모든 정보를 입력해주세요.")

# [화면 2: 참여하기]
elif st.session_state.page == 'join':
    st.title("🔗 팀 참여하기")
    code_in = st.text_input("초대 코드 6자리").upper()
    u_name = st.text_input("내 닉네임")
    
    if st.button("입장"):
        try:
            res = supabase.table("team").select("*").eq("invite_code", code_in).execute()
            if res.data:
                team_data = res.data[0]
                members = team_data['members']
                if not any(m['name'] == u_name for m in members):
                    members.append({"name": u_name, "status": "✅ 대기"})
                    supabase.table("team").update({"members": members}).eq("invite_code", code_in).execute()
                
                st.session_state.update({
                    "invite_code": code_in,
                    "my_name": u_name,
                    "page": "dashboard"
                })
                st.rerun()
            else:
                st.error("존재하지 않는 코드입니다.")
        except Exception as e:
            st.error(f"참여 실패: {e}")

# [화면 3: 대시보드]
elif st.session_state.page == 'dashboard':
    try:
        res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
        if not res.data:
            st.error("데이터를 찾을 수 없습니다.")
            st.stop()
        
        data = res.data[0]
        st.title(f"🏫 {data['team_name']}")
        st.info(f"초대코드: {st.session_state.invite_code} | 사용자: {st.session_state.my_name}")

        # 팀원 현황
        st.subheader("👥 팀원 상태")
        m_cols = st.columns(5)
        for idx, m in enumerate(data['members']):
            with m_cols[idx % 5]:
                st.markdown(f"**{m['name']}**\n\n{m['status']}")

        st.divider()

        # 과목 탭
        subjects = data['subjects']
        if subjects:
            tabs = st.tabs(list(subjects.keys()))
            for i, tab in enumerate(tabs):
                s_name = list(subjects.keys())[i]
                with tab:
                    up_file = st.file_uploader(f"{s_name} 자료", key=f"file_{s_name}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"🚀 {s_name} 열공 시작", key=f"start_{s_name}"):
                            update_db_status(f"🔥 {s_name} 공부중")
                            st.rerun()
                    with c2:
                        if st.button(f"🏁 공부 종료 & 퀴즈", key=f"end_{s_name}"):
                            update_db_status("✅ 완료")
                            if up_file:
                                with st.spinner("AI 퀴즈 생성 중..."):
                                    # 파일 이름/내용 기반 퀴즈 생성 (간단화)
                                    prompt = f"다음 과목에 대한 퀴즈 3개를 내줘: {s_name}. 자료이름: {up_file.name}"
                                    response = model.generate_content(prompt)
                                    st.write("🤖 AI 퀴즈:")
                                    st.write(response.text)
                            else:
                                st.warning("파일이 없습니다.")
        
        if st.button("🔄 새로고침"):
            st.rerun()

    except Exception as e:
        st.error(f"대시보드 로딩 오류: {e}")
