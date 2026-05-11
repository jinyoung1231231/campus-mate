import streamlit as st
import random
import string

# --- 1. 초기 설정 및 세션 초기화 ---
st.set_page_config(page_title="Check-Mate", page_icon="🔥", layout="wide")

# 가상의 데이터베이스 역할을 할 세션 상태 데이터
if 'page' not in st.session_state:
    st.session_state.page = 'gate'  # gate -> landing -> dashboard
if 'team_members' not in st.session_state:
    st.session_state.team_members = []  # 현재 팀원 리스트
if 'invite_code' not in st.session_state:
    st.session_state.invite_code = ""
if 'study_active' not in st.session_state:
    st.session_state.study_active = False
if 'my_goal_grade' not in st.session_state:
    st.session_state.my_goal_grade = ""

# --- 2. 스타일링 ---
st.markdown("""
    <style>
    .team-slot {
        border: 2px solid #eee; border-radius: 12px;
        padding: 10px; text-align: center; background-color: white;
        min-height: 80px;
    }
    .status-fire { color: #FF4B4B; font-weight: bold; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 화면 0: 게이트웨이 (팀 만들기 vs 합류하기) ---
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.subheader("함께 공부할 팀을 선택하세요")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 새로운 팀 만들기", use_container_width=True):
            st.session_state.page = 'landing'
            st.rerun()
    with col2:
        if st.button("🔗 초대 코드로 합류하기", use_container_width=True):
            st.session_state.page = 'join'
            st.rerun()

# --- 화면 1-1: 팀 생성 (Landing) ---
elif st.session_state.page == 'landing':
    st.title("🏗️ 팀 생성하기")
    with st.form("create_team"):
        t_name = st.text_input("우리 팀 이름", placeholder="예: 경제학 찢는 10인")
        t_icon = st.selectbox("팀 아이콘", ["🔥 불꽃", "📚 책", "🚀 로켓", "💡 아이디어"])
        career = st.radio("진로 결정 여부", ["정했다", "탐색 중"], horizontal=True)
        my_name = st.text_input("나의 닉네임", placeholder="예: 과탑선배")
        
        if st.form_submit_button("팀 생성 및 입장"):
            if t_name and my_name:
                # 6자리 랜덤 초대 코드 생성
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                st.session_state.invite_code = code
                st.session_state.user_info = {"team_name": t_name, "icon": t_icon, "career": career, "name": my_name}
                st.session_state.team_members = [{"name": my_name, "status": "✅"}]
                st.session_state.page = 'dashboard'
                st.rerun()

# --- 화면 1-2: 팀 합류 (Join) ---
elif st.session_state.page == 'join':
    st.title("🔗 팀 합류하기")
    code_input = st.text_input("초대 코드를 입력하세요 (6자리)", placeholder="예: AB12CD")
    join_name = st.text_input("나의 닉네임", placeholder="예: 열공맨")
    
    if st.button("팀 입장하기"):
        if code_input and join_name:
            # (실제로는 DB에서 코드를 찾겠지만, 여기선 임시로 입장 허용)
            st.session_state.invite_code = code_input
            st.session_state.user_info = {"team_name": "기존 팀", "icon": "🔥", "career": "탐색 중", "name": join_name}
            # 기존 멤버에 나를 추가 (가상 시뮬레이션)
            st.session_state.team_members = [{"name": "팀장님", "status": "🔥"}, {"name": join_name, "status": "✅"}]
            st.session_state.page = 'dashboard'
            st.rerun()

# --- 화면 2: 대시보드 (Dashboard) ---
elif st.session_state.page == 'dashboard':
    info = st.session_state.user_info
    
    # 상단 헤더 (초대 코드 표시)
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title(f"{info['icon'].split()[0]} {info['team_name']}")
        st.info(f"🎫 초대 코드: **{st.session_state.invite_code}** (친구에게 공유하세요!)")
    with col_h2:
        st.session_state.my_goal_grade = st.text_input("🎯 목표 학점", value=st.session_state.my_goal_grade)

    # 10인 슬롯 영역 (실제 데이터 반영)
    st.write("### 👥 실시간 팀원 상태")
    cols = st.columns(10)
    
    # 현재 세션에 저장된 팀원 리스트를 슬롯에 배치
    for i in range(10):
        with cols[i]:
            if i < len(st.session_state.team_members):
                member = st.session_state.team_members[i]
                # 내가 공부 시작을 누르면 내 상태 실시간 업데이트
                display_status = "🔥" if (member['name'] == info['name'] and st.session_state.study_active) else member['status']
                st.markdown(f"<div class='team-slot'><b>{member['name']}</b><br><span class='status-fire'>{display_status}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='team-slot' style='color:#ccc;'><br>Empty</div>", unsafe_allow_html=True)

    st.divider()

    # 중앙: 스케줄러 & 지표 (생략된 기존 로직 유지)
    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        st.subheader("📅 역산형 스케줄러")
        day_slider = st.select_slider("단계 선택", options=["1일차", "2일차", "3일차"])
        uploaded_file = st.file_uploader("📂 공부 자료 업로드", type=['pdf', 'png', 'jpg'])
        
        if not st.session_state.study_active:
            if st.button("🚀 공부 시작", use_container_width=True):
                st.session_state.study_active = True
                st.rerun()
        else:
            if st.button("🏁 종료 및 퀴즈", use_container_width=True):
                st.session_state.study_active = False
                st.rerun()

    with col_right:
        st.subheader("📊 학습 리포트")
        st.metric("학습 효율", "+15%", delta="상승 중")
        if st.button("🏠 처음으로 (테스트용)"):
            st.session_state.page = 'gate'
            st.rerun()
