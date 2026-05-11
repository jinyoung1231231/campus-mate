import streamlit as st
import random
import string
import time

# --- 1. 초기 설정 및 세션 초기화 ---
st.set_page_config(page_title="Check-Mate", page_icon="🔥", layout="wide")

# 가상 DB (실제 배포 시에는 Firebase나 전역 데이터 저장소를 사용해야 함)
# 여기서는 세션 간 데이터 공유를 시뮬레이션하기 위해 '팀 코드'를 Key로 사용합니다.
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""

# --- 2. 화면 0: 게이트웨이 ---
if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate: 실시간 멀티 학습")
    st.subheader("팀원들과 실시간으로 연결됩니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 새로운 팀 만들기", use_container_width=True):
            st.session_state.page = 'create_team'
            st.rerun()
    with col2:
        if st.button("🔗 초대 코드로 합류하기", use_container_width=True):
            st.session_state.page = 'join_team'
            st.rerun()

# --- 화면 1: 팀 생성 (DB 등록 시뮬레이션) ---
elif st.session_state.page == 'create_team':
    st.title("🏗️ 새로운 팀 생성")
    with st.form("create_form"):
        t_name = st.text_input("팀 이름", placeholder="공학도들의 밤샘")
        my_nick = st.text_input("나의 닉네임")
        sub_count = st.number_input("관리할 과목 개수", 1, 10, 3)
        
        if st.form_submit_button("팀 생성하기"):
            # 랜덤 초대코드 생성 및 초기화
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            st.session_state.invite_code = code
            st.session_state.team_name = t_name
            st.session_state.my_name = my_nick
            # 과목 데이터 초기화
            st.session_state.subjects = {f"과목 {i+1}": {"grade": "A+", "files": []} for i in range(sub_count)}
            # 실제 DB라면 여기에 데이터를 Insert함
            st.session_state.page = 'dashboard'
            st.rerun()

# --- 화면 2: 초대 코드로 합류 (실제 멀티 핵심) ---
elif st.session_state.page == 'join_team':
    st.title("🔗 초대 코드로 팀 합류")
    code_input = st.text_input("초대 코드 6자리를 입력하세요")
    my_nick = st.text_input("나의 닉네임")
    
    if st.button("팀 입장"):
        if len(code_input) == 6 and my_nick:
            # 원래는 DB에서 code_input에 해당하는 팀을 조회함
            st.session_state.invite_code = code_input.upper()
            st.session_state.my_name = my_nick
            st.session_state.team_name = "참여 중인 팀" # 실제론 DB에서 가져옴
            st.session_state.subjects = {"경제학": {"grade": "A+", "files": []}}
            st.session_state.page = 'dashboard'
            st.success(f"{code_input} 팀에 합류했습니다!")
            st.rerun()

# --- 화면 3: 실시간 대시보드 ---
elif st.session_state.page == 'dashboard':
    # 상단 정보
    st.title(f"🔥 {st.session_state.team_name}")
    st.write(f"🎫 초대 코드: **{st.session_state.invite_code}** | 사용자: **{st.session_state.my_name}**")

    # [실시간 동기화 영역]
    # 실제로는 주기적으로 DB를 읽어서 업데이트해야 함 (st_autorefresh 사용 가능)
    st.write("### 👥 실시간 팀원 상태 (10인 슬롯)")
    
    # 예시: DB에서 가져온 팀원 데이터 리스트
    # (실제 환경에선 이 리스트가 DB 업데이트에 따라 실시간으로 변함)
    team_members = [
        {"name": st.session_state.my_name, "status": "🔥 공부중" if st.session_state.get('study_active', False) else "✅ 대기"},
        {"name": "철수(친구)", "status": "🔥 공부중"}, # 친구의 데이터 시뮬레이션
    ]
    
    cols = st.columns(10)
    for i in range(10):
        with cols[i]:
            if i < len(team_members):
                m = team_members[i]
                color = "red" if "🔥" in m['status'] else "green"
                st.markdown(f"""
                    <div style="border: 2px solid {color}; border-radius: 10px; padding: 10px; text-align: center;">
                        <b>{m['name']}</b><br>{m['status']}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='border: 1px dashed #ccc; border-radius: 10px; padding: 10px; text-align: center; color: #ccc;'>Empty</div>", unsafe_allow_html=True)

    st.divider()

    # 과목별 멀티 관리
    st.subheader("📚 과목별 목표 및 자료")
    tabs = st.tabs(list(st.session_state.subjects.keys()))
    
    for i, tab in enumerate(tabs):
        sub_name = list(st.session_state.subjects.keys())[i]
        with tab:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"**{sub_name}** 목표 학점: {st.session_state.subjects[sub_name]['grade']}")
                st.file_uploader(f"{sub_name} 자료 업로드", key=f"file_{sub_name}")
            with c2:
                if not st.session_state.get('study_active', False):
                    if st.button(f"🚀 {sub_name} 공부 시작", key=f"start_{sub_name}"):
                        st.session_state.study_active = True
                        st.rerun()
                else:
                    if st.button(f"🏁 {sub_name} 종료", key=f"stop_{sub_name}"):
                        st.session_state.study_active = False
                        st.rerun()
