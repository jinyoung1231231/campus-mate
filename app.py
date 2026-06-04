import streamlit as st
from supabase import create_client

# 1. 최상단에서 세션 상태 초기화 (가장 중요)
session_defaults = {
    'page': 'gate', 
    'my_name': '', 
    'invite_code': '', 
    'current_mode': 'dashboard'
}
for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 2. 데이터베이스 연결
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# 3. 데이터 로드 (세션 변수가 안전하게 존재하는 상태에서 실행)
data = None
if st.session_state.invite_code:
    try:
        res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
        if res.data: data = res.data[0]
    except: pass

# 4. 앱 레이아웃
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임 입력")
    ci = st.text_input("초대코드 입력")
    if st.button("입장"):
        if un and ci:
            st.session_state.my_name = un
            st.session_state.invite_code = ci
            st.session_state.page = 'dashboard'
            st.rerun()

elif st.session_state.page == 'dashboard':
    if not data:
        st.warning("유효하지 않은 워크스페이스입니다.")
        if st.button("뒤로가기"):
            st.session_state.page = 'gate'
            st.rerun()
    else:
        st.header(f"{data.get('team_name', '팀')}")
        st.write("대시보드 정상 로드 완료")
