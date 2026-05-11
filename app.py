import streamlit as st
import pandas as pd

# --- 1. 초기 설정 및 세션 초기화 ---
st.set_page_config(page_title="Check-Mate", page_icon="🔥", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'landing'
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'study_active' not in st.session_state:
    st.session_state.study_active = False
if 'my_goal_grade' not in st.session_state:
    st.session_state.my_goal_grade = ""

# --- 2. 스타일링 (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .team-slot {
        border: 2px solid #eee; border-radius: 12px;
        padding: 10px; text-align: center; background-color: white;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
    }
    .status-fire { color: #FF4B4B; font-weight: bold; }
    .metric-card {
        background-color: white; padding: 20px;
        border-radius: 10px; border: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 화면 1: 팀 생성 및 진로 설정 (Landing Page) ---
if st.session_state.page == 'landing':
    st.title("🔥 Check-Mate")
    st.subheader("나만의 AI 감독관과 팀 프로젝트를 시작하세요")
    
    with st.form("init_form"):
        st.write("### 📝 초기 설정")
        t_name = st.text_input("우리 팀 이름", placeholder="예: 밤샘 코딩 멸공단")
        t_icon = st.selectbox("팀 아이콘 선택", ["🔥 불꽃", "📚 책", "🚀 로켓", "☕ 커피", "💡 아이디어"])
        
        career = st.radio("현재 진로를 정하셨나요?", ["정했다", "아직 탐색 중이다"], horizontal=True)
        goal_career = st.text_input("나의 최종 꿈/진로 (선택)", placeholder="예: 데이터 분석가, 금융권 취업 등")
        
        submitted = st.form_submit_button("팀 생성 및 입장 🚀")
        if submitted:
            if t_name:
                st.session_state.user_info = {
                    "team_name": t_name,
                    "icon": t_icon,
                    "career": career,
                    "goal_career": goal_career
                }
                st.session_state.page = 'dashboard'
                st.rerun()
            else:
                st.error("팀 이름을 입력해 주세요!")

# --- 4. 화면 2: 메인 대시보드 (Main Dashboard) ---
elif st.session_state.page == 'dashboard':
    info = st.session_state.user_info
    
    # [헤더 영역]
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title(f"{info['icon'].split()[0]} {info['team_name']}")
        st.caption(f"🎯 진로: {info['goal_career'] if info['goal_career'] else '탐색 중'} | 상태: {info['career']}")
    with col_h2:
        # 목표 학점 실시간 입력
        st.session_state.my_goal_grade = st.text_input("🎯 목표 학점", value=st.session_state.my_goal_grade, placeholder="예: 4.5")

    st.divider()

    # [10인 슬롯 영역]
    st.write("### 👥 실시간 팀원 상태")
    cols = st.columns(10)
    mock_members = [("나", "🔥"), ("철수", "🔥"), ("영희", "✅"), ("민수", "💤"), ("지수", "🔥"), "", "", "", "", ""]
    for i in range(10):
        with cols[i]:
            if mock_members[i]:
                name, stat = mock_members[i]
                st.markdown(f"<div class='team-slot'><b>{name}</b><br><span class='status-fire'>{stat}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='team-slot' style='color:#ccc;'><br>Empty</div>", unsafe_allow_html=True)

    st.write("")
    st.divider()

    # [중앙 로직: 스케줄러 & 지표]
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.subheader("📅 역산형 스케줄러")
        d_day = st.date_input("시험/과제 마감일 선택")
        split_days = st.number_input("분할 공부 일수", min_value=1, max_value=14, value=3)
        
        st.write(f"**[{d_day} 마감]** AI가 추천하는 {split_days}일 플랜입니다.")
        day_slider = st.select_slider("오늘 할 일 선택", options=[f"{i+1}일차" for i in range(split_days)])
        
        # 파일 업로드 (스스로 분석을 위한 핵심)
        st.write("---")
        uploaded_file = st.file_uploader(f"📂 {day_slider} 공부 자료 업로드 (AI 분석용)", type=['pdf', 'png', 'jpg'])
        
        if uploaded_file:
            st.success(f"'{uploaded_file.name}' 자료가 준비되었습니다. 종료 후 퀴즈가 생성됩니다.")

        if not st.session_state.study_active:
            if st.button("🚀 공부 시작", use_container_width=True, disabled=(uploaded_file is None)):
                st.session_state.study_active = True
                st.rerun()
            if uploaded_file is None:
                st.caption("⚠️ 자료를 먼저 업로드해야 '공부 시작'이 가능합니다.")
        else:
            st.error("⏱️ AI 감독관 모드 작동 중... 집중하세요!")
            if st.button("🏁 종료 및 퀴즈 풀기", use_container_width=True):
                st.session_state.study_active = False
                st.balloons()
                st.info("AI가 파일 내용을 분석하여 퀴즈를 생성하고 있습니다...")

    with col_right:
        st.subheader("📊 학습 리포트")
        m1, m2 = st.columns(2)
        m1.metric("나의 상승률", "+15.2%", delta="전주 대비")
        m2.metric("팀 평균 온도", "85°C", delta="3°C")
        
        st.write("")
        st.markdown("""
        <div class='metric-card'>
        <b>📍 AI 취약점 진단</b><br>
        최근 퀴즈에서 <b>'한계 비용'</b> 관련 오답이 많습니다.<br>
        <span style='color:red;'>[실수 2회 / 개념 모름 1회]</span><br>
        오늘 공부 종료 후 이 부분을 집중적으로 낼게요!
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("☕ 커피 타임 선언 (팀 목표 달성 시)"):
            st.toast("팀원들에게 커피 타임 알림을 보냈습니다!")

    # [하단: 팀 게시판]
    st.divider()
    st.subheader("📋 팀 실시간 요약 피드")
    st.chat_message("ai").write("**지수** 님이 1일차 공부를 완료했습니다! \n\n 핵심 요약: 오늘 공부한 파트에서 가장 중요한 건 '탄력성 공식'입니다. 무조건 외우세요!")
