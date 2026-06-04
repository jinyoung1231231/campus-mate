import streamlit as st
from supabase import create_client
import time

# 1. CSS
st.markdown("""<style>
    .stApp { background-color: #ffffff; color: #37352f; }
    .subject-block { background-color: #fbfbfa; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
</style>""", unsafe_allow_html=True)

# 2. 초기화 (예외처리 추가)
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = init_db()

# 3. 세션 및 데이터 로드
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_name' not in st.session_state: st.session_state.my_name = ''

# 데이터 로드
data = None
if st.session_state.invite_code:
    try:
        res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
        if res.data: data = res.data[0]
    except Exception:
        st.error("데이터를 불러오는 중 오류가 발생했습니다.")

# 4. 화면 렌더링
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임 입력")
    ci = st.text_input("초대코드 입력")
    if st.button("입장"):
        if un and ci:
            st.session_state.update({'my_name': un, 'invite_code': ci, 'page': 'dashboard'})
            st.rerun()

elif st.session_state.page == 'dashboard':
    if not data:
        st.warning("초대코드가 잘못되었거나 팀 정보가 없습니다.")
        if st.button("처음으로"):
            st.session_state.page = 'gate'
            st.rerun()
    else:
        st.header(f"{data.get('team_name', '워크스페이스')}")
        
        # 메뉴
        menu = st.sidebar.radio("메뉴", ["학습 보드", "상담소"])
        
        if menu == "학습 보드":
            subjects = data.get('subjects', {}).get(st.session_state.my_name, [])
            if not subjects:
                st.info("등록된 과목이 없습니다.")
            else:
                for sub in subjects:
                    st.markdown(f"""<div class='subject-block'>
                                <h3>📚 {sub['name']}</h3>
                                <p>진행도: {sub.get('current_day', 1)} / {sub.get('total_days', 7)}일</p>
                                </div>""", unsafe_allow_html=True)
                    with st.expander("일정 확인"):
                        st.write("Day 1: 기본 개념 정독")
                        st.write("Day 2: 코드 예제 실습")
                        
        elif menu == "상담소":
            st.subheader("🔮 AI 상담소")
            q = st.text_area("고민을 입력하세요")
            if st.button("답변 받기"):
                st.write("AI가 고민을 분석 중입니다... (상담 로직이 작동합니다)")
