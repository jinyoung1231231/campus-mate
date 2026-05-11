import streamlit as st
import pandas as pd
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Check-Mate", page_icon="🔥", layout="wide")

# --- 세션 상태 관리 (데이터 저장용) ---
if 'page' not in st.session_state:
    st.session_state.page = 'landing' # landing -> dashboard
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'study_active' not in st.session_state:
    st.session_state.study_active = False

# --- 스타일링 ---
st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #FF4B4B; }
    .team-slot {
        border: 2px solid #f0f2f6; border-radius: 15px;
        padding: 10px; text-align: center; background-color: white;
    }
    .metric-box {
        background-color: #f8f9fa; padding: 15px;
        border-radius: 10px; border-left: 5px solid #FF4B4B;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 화면 1: 팀 생성 및 진로 설정 (Landing) ---
if st.session_state.page == 'landing':
    st.title("🔥 Check-Mate: 팀 학습 관리 시스템")
    st.subheader("새로운 팀을 만들고 학습을 시작하세요.")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            team_name = st.text_input("1. 우리 팀의 이름을 정해주세요", placeholder="예: 밤샘 코딩 멸공단")
            team_icon = st.selectbox("2. 팀 아이콘 프리셋 선택", ["🔥 불꽃", "📚 책", "🚀 로켓", "☕ 커피", "💡 아이디어"])
        
        with col2:
            career_status = st.radio("3. 현재 진로를 정하셨나요?", ["정했다", "아직 탐색 중이다"])
            goal = st.text_input("목표 성적 또는 최종 목적지", placeholder="예: 미시경제학 A+, 금융권 취업")

    if st.button("팀 생성 및 입장 🚀", use_container_width=True):
        if team_name:
            st.session_state.user_info = {
                "team_name": team_name,
                "icon": team_icon,
                "career": career_status,
                "goal": goal
            }
            st.session_state.page = 'dashboard'
            st.rerun()
        else:
            st.warning("팀 이름을 입력해야 합니다!")

# --- 화면 2: 메인 대시보드 (Dashboard) ---
elif st.session_state.page == 'dashboard':
    info = st.session_state.user_info
    
    # 상단 헤더
    st.title(f"{info['icon'].split()[0]} {info['team_name']}")
    
    # 진로 설정 기반 AI 메시지
    if info['career'] == "정했다":
        st.caption(f"🎯 **AI 조언:** 목표하신 '{info['goal']}'을(를) 향한 최단 루트를 계산 중입니다. 오늘 분량을 끝내면 합격률이 올라갑니다!")
    else:
        st.caption("🔍 **AI 조언:** 아직 진로를 탐색 중이시군요? 오늘 공부를 통해 본인의 적성을 확인해 봅시다!")

    st.divider()

    # 1. 10인 팀 상태창 (열품타 스타일)
    cols = st.columns(10)
    names = ["나", "철수", "영희", "민수", "지수", "", "", "", "", ""]
    for i in range(10):
        with cols[i]:
            if names[i]:
                status = "🔥" if i < 3 else "💤"
                st.markdown(f"<div class='team-slot'><b>{names[i]}</b><br>{status}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='team-slot' style='color:#ccc;'>Empty</div>", unsafe_allow_html=True)

    st.write("")
    
    # 2. 중앙 레이아웃: 스케줄러 & 지표
    left_col, right_col = st.columns([1.2, 1])
    
    with left_col:
        st.subheader("📅 역산형 스케줄러")
        d_day = st.date_input("시험/과제 마감일 선택")
        total_days = st.number_input("며칠 동안 나눠서 공부할까요?", min_value=1, max_value=30, value=3)
        
        st.write(f"**[{d_day} 마감]** 총 {total_days}일 플랜:")
        selected_day = st.select_slider("현재 단계", options=[f"{i+1}일차" for i in range(total_days)])
        
        st.info(f"오늘의 미션: {selected_day} 목표 범위를 완독하고 AI 퀴즈에 응시하세요.")
        
        if not st.session_state.study_active:
            if st.button("🚀 공부 시작", use_container_width=True):
                st.session_state.study_active = True
                st.rerun()
        else:
            st.warning("공부 기록 중... (타이머 작동 중)")
            if st.button("🏁 종료 및 퀴즈 풀기", use_container_width=True):
                st.session_state.study_active = False
                st.success("공부 완료! 퀴즈 모듈로 진입합니다.")

    with right_col:
        st.subheader("📊 학습 성과 지표")
        c1, c2 = st.columns(2)
        c1.metric("학습 효율 상승률", "+15.2%", delta="전주 대비")
        c2.metric("팀 전체 열정 온도", "82°C", delta="5°C")
        
        st.write("")
        st.markdown("""
        <div class='metric-box'>
        <b>📍 AI 핀셋 약점 공략</b><br>
        지난 퀴즈 분석 결과: <b>'공급 탄력성 공식'</b>에서 오답 사유(개념 모름)가 2회 감지되었습니다. 
        해당 파트 요약본을 다시 읽어볼까요?
        </div>
        """, unsafe_allow_html=True)

    # 3. 하단 게시판
    st.divider()
    st.subheader("📋 팀 공유 게시판 (AI 자동 요약)")
    st.chat_message("ai").write("**철수** 님이 1일차 공부를 완료했습니다! \n\n 핵심 요약: 기회비용은 선택 시 포기한 가치 중 최대값입니다. 절대 비용과 헷갈리지 마세요!")
