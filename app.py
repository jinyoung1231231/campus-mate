import streamlit as st
import random
import string

# --- 1. 초기 설정 및 세션 초기화 ---
st.set_page_config(page_title="Check-Mate", page_icon="🔥", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'team_members' not in st.session_state:
    st.session_state.team_members = []
if 'subjects' not in st.session_state:
    st.session_state.subjects = {} # 과목별 데이터 저장 {과목명: {목표: , 파일: , 일정: }}
if 'study_active' not in st.session_state:
    st.session_state.study_active = False

# --- 2. 스타일링 ---
st.markdown("""
    <style>
    .team-slot {
        border: 2px solid #eee; border-radius: 12px;
        padding: 10px; text-align: center; background-color: white;
        min-height: 80px; box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
    }
    .status-fire { color: #FF4B4B; font-weight: bold; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    .subject-card {
        padding: 15px; border-radius: 10px; background-color: #f8f9fa;
        border-left: 5px solid #FF4B4B; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 화면 0: 게이트웨이 ---
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    st.subheader("나만의 팀 학습 대시보드")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 새로운 팀 만들기", use_container_width=True):
            st.session_state.page = 'landing'
            st.rerun()
    with col2:
        if st.button("🔗 초대 코드로 합류하기", use_container_width=True):
            st.session_state.page = 'join'
            st.rerun()

# --- 화면 1: 팀 생성 (초기 과목 개수 설정 포함) ---
elif st.session_state.page == 'landing':
    st.title("🏗️ 팀 생성 및 과목 설정")
    with st.form("create_team"):
        t_name = st.text_input("우리 팀 이름", placeholder="예: 경영학과 A+ 멸공단")
        my_name = st.text_input("나의 닉네임", placeholder="예: 열공대장")
        subject_count = st.number_input("이번 학기 관리할 과목 개수", min_value=1, max_value=10, value=3)
        
        if st.form_submit_button("팀 생성 및 과목 입력하기"):
            if t_name and my_name:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                st.session_state.invite_code = code
                st.session_state.user_info = {"team_name": t_name, "icon": "🔥", "name": my_name, "sub_count": subject_count}
                st.session_state.team_members = [{"name": my_name, "status": "✅"}]
                st.session_state.page = 'subject_init'
                st.rerun()

# --- 화면 1-2: 과목 정보 초기 입력 ---
elif st.session_state.page == 'subject_init':
    st.title("📚 과목별 목표 설정")
    st.write("각 과목의 이름과 목표 학점을 입력해주세요.")
    
    with st.form("subject_form"):
        temp_subjects = {}
        for i in range(st.session_state.user_info['sub_count']):
            col1, col2 = st.columns(2)
            with col1:
                sub_name = st.text_input(f"과목 {i+1} 이름", value=f"과목 {i+1}")
            with col2:
                sub_grade = st.selectbox(f"과목 {i+1} 목표 학점", ["A+", "A0", "B+", "B0", "PASS"], key=f"grade_{i}")
            temp_subjects[sub_name] = {"grade": sub_grade, "file": None, "plan": 3}
        
        if st.form_submit_button("설정 완료 및 대시보드 입장"):
            st.session_state.subjects = temp_subjects
            st.session_state.page = 'dashboard'
            st.rerun()

# --- 화면 2: 대시보드 (멀티 과목 지원) ---
elif st.session_state.page == 'dashboard':
    info = st.session_state.user_info
    
    # 상단 헤더
    st.title(f"🔥 {info['team_name']}")
    st.info(f"🎫 초대 코드: **{st.session_state.invite_code}** | 현재 관리 중인 과목: {len(st.session_state.subjects)}개")

    # 10인 슬롯 영역
    cols = st.columns(10)
    for i in range(10):
        with cols[i]:
            if i < len(st.session_state.team_members):
                member = st.session_state.team_members[i]
                display_status = "🔥 공부중" if (member['name'] == info['name'] and st.session_state.study_active) else "✅ 대기"
                st.markdown(f"<div class='team-slot'><b>{member['name']}</b><br><span class='status-fire'>{display_status}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='team-slot' style='color:#ccc;'><br>Empty</div>", unsafe_allow_html=True)

    st.divider()

    # 중앙: 멀티 과목 탭 시스템
    st.subheader("📖 과목별 학습 관리")
    tabs = st.tabs(list(st.session_state.subjects.keys()))

    for i, tab in enumerate(tabs):
        sub_name = list(st.session_state.subjects.keys())[i]
        with tab:
            col_left, col_right = st.columns([1.5, 1])
            
            with col_left:
                st.markdown(f"""
                <div class='subject-card'>
                    <h4>{sub_name}</h4>
                    <b>목표 학점: {st.session_state.subjects[sub_name]['grade']}</b>
                </div>
                """, unsafe_allow_html=True)
                
                # 역산형 스케줄러 & 파일 업로드
                d_day = st.date_input(f"{sub_name} 시험/마감일", key=f"date_{sub_name}")
                split = st.slider(f"분할 일수 (며칠 공부할까요?)", 1, 14, 3, key=f"slider_{sub_name}")
                
                uploaded_file = st.file_uploader(f"📂 {sub_name} 공부 자료(PDF/이미지) 업로드", type=['pdf', 'png', 'jpg'], key=f"file_{sub_name}")
                
                if uploaded_file:
                    st.session_state.subjects[sub_name]['file'] = uploaded_file.name
                    st.success(f"'{uploaded_file.name}' 자료가 준비되었습니다.")

            with col_right:
                st.write("### 🚀 실행")
                day_select = st.select_slider(f"{sub_name} 진행 단계", options=[f"{d+1}일차" for d in range(split)], key=f"day_{sub_name}")
                
                if not st.session_state.study_active:
                    if st.button(f"🔥 {sub_name} 공부 시작", use_container_width=True, key=f"btn_{sub_name}"):
                        if uploaded_file:
                            st.session_state.study_active = True
                            st.rerun()
                        else:
                            st.error("파일을 먼저 업로드해주세요!")
                else:
                    st.error("⏱️ 현재 공부 기록 중...")
                    if st.button(f"🏁 {sub_name} 종료 및 퀴즈", use_container_width=True, key=f"stop_{sub_name}"):
                        st.session_state.study_active = False
                        st.rerun()

    # 하단 처음으로 버튼 (테스트용)
    if st.button("🏠 초기화 (테스트용)"):
        st.session_state.clear()
        st.rerun()
