import streamlit as st

# --- 세션 상태 초기화 추가 ---
if 'my_goal_grade' not in st.session_state:
    st.session_state.my_goal_grade = "미설정"

# --- [수정] 대시보드 상단: 팀 정보 및 개인 목표 ---
elif st.session_state.page == 'dashboard':
    info = st.session_state.user_info
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.title(f"{info['icon'].split()[0]} {info['team_name']}")
    with col_t2:
        # 팀 합류 후 목표 학점 설정
        new_grade = st.text_input("🎯 나의 목표 학점", value=st.session_state.my_goal_grade)
        st.session_state.my_goal_grade = new_grade

    st.caption(f"🚀 현재 목표: {st.session_state.my_goal_grade} | 진로 상태: {info['career']}")
    st.divider()

    # --- [추정] 10인 슬롯 중 '나'의 카드에 목표 학점 표시 ---
    # (생략: 기존 10인 슬롯 코드 유지하되 '나' 부분에 목표 학점 툴팁 추가 가능)

    # --- [수정] 중앙 좌측: 스케줄러 및 파일 업로드 ---
    left_col, right_col = st.columns([1.2, 1])
    
    with left_col:
        st.subheader("📅 역산형 스케줄러")
        # ... (기존 D-Day 설정 코드) ...
        
        selected_day = st.select_slider("현재 단계", options=[f"{i+1}일차" for i in range(3)]) # 예시 3일
        
        # 🔥 파일 업로드 기능 추가
        uploaded_file = st.file_uploader(f"{selected_day} 공부 자료 업로드 (PDF, JPG)", type=['pdf', 'jpg', 'png'])
        
        if uploaded_file:
            st.success(f"✅ {uploaded_file.name} 분석 완료! 공부 종료 후 이 자료에서 퀴즈가 출제됩니다.")
        
        if not st.session_state.study_active:
            # 파일이 있을 때만 시작 버튼 활성화 (선택 사항)
            start_btn = st.button("🚀 공부 시작", use_container_width=True, disabled=(uploaded_file is None))
            if uploaded_file is None:
                st.caption("⚠️ 자료를 먼저 업로드해야 AI가 퀴즈를 준비할 수 있습니다.")
            if start_btn:
                st.session_state.study_active = True
                st.rerun()
        else:
            st.warning("⏱️ AI 감독관이 지켜보고 있습니다... 몰입하세요!")
            if st.button("🏁 종료 및 퀴즈 풀기", use_container_width=True):
                # 여기에 나중에 AI 퀴즈 로직 연결
                st.session_state.study_active = False
                st.balloons()
                st.info("AI가 파일 내용을 분석해 퀴즈를 생성 중입니다. 잠시만 기다려주세요...")

    # ... (이하 생략) ...
