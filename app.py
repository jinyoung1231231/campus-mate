import streamlit as st

from supabase import create_client, Client

import random

import string



# --- [필독] 여기에 본인의 Supabase 정보를 복사해서 넣으세요 ---

SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co/rest/v1/"

SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"



# 서버 연결 비서 생성

try:

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

except:

    st.error("Supabase URL이나 Key가 잘못되었습니다. 상단 코드를 확인해주세요.")



# --- 세션 상태 초기화 ---

if 'page' not in st.session_state:

    st.session_state.page = 'gate'

if 'my_name' not in st.session_state:

    st.session_state.my_name = ""



# --- 화면 0: 게이트웨이 (팀 만들기 vs 합류하기) ---

if st.session_state.page == 'gate':

    st.title("🔥 Check-Mate: 실시간 멀티")

    col1, col2 = st.columns(2)

    with col1:

        if st.button("🆕 팀 새로 만들기", use_container_width=True):

            st.session_state.page = 'create'

            st.rerun()

    with col2:

        if st.button("🔗 초대코드로 합류", use_container_width=True):

            st.session_state.page = 'join'

            st.rerun()



# --- 화면 1: 팀 생성 (DB 저장) ---

elif st.session_state.page == 'create':

    st.subheader("🏗️ 새로운 팀 생성")

    with st.form("create_form"):

        t_name = st.text_input("팀 이름")

        my_nick = st.text_input("내 닉네임")

        sub_count = st.number_input("과목 수", 1, 5, 2)

        if st.form_submit_button("팀 생성 및 서버 등록"):

            if t_name and my_nick:

                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

                # DB 저장 데이터 구성

                initial_members = [{"name": my_nick, "status": "✅ 대기"}]

                initial_subjects = {f"과목{i+1}": {"grade": "A+"} for i in range(sub_count)}

                

                # Supabase에 데이터 한 줄 추가 (Insert)

                supabase.table("teams").insert({

                    "invite_code": code,

                    "team_name": t_name,

                    "members": initial_members,

                    "subjects": initial_subjects

                }).execute()

                

                st.session_state.update({"invite_code": code, "my_name": my_nick, "page": "dashboard"})

                st.rerun()



# --- 화면 2: 팀 합류 (DB 검색) ---

elif st.session_state.page == 'join':

    st.subheader("🔗 팀 합류하기")

    code_input = st.text_input("초대 코드 6자리").upper()

    my_nick = st.text_input("내 닉네임")

    if st.button("입장하기"):

        # DB에서 해당 코드가 있는지 검색 (Select)

        res = supabase.table("teams").select("*").eq("invite_code", code_input).execute()

        if res.data:

            team_data = res.data[0]

            members = team_data['members']

            # 기존 멤버에 나를 추가

            if not any(m['name'] == my_nick for m in members):

                members.append({"name": my_nick, "status": "✅ 대기"})

                supabase.table("teams").update({"members": members}).eq("invite_code", code_input).execute()

            

            st.session_state.update({"invite_code": code_input, "my_name": my_nick, "page": "dashboard"})

            st.rerun()

        else:

            st.error("잘못된 코드입니다. 다시 확인해주세요!")



# --- 화면 3: 메인 대시보드 (실시간 연동) ---

elif st.session_state.page == 'dashboard':

    # 1. 서버에서 최신 데이터 가져오기

    res = supabase.table("teams").select("*").eq("invite_code", st.session_state.invite_code).execute()

    if not res.data: st.stop()

    

    data = res.data[0]

    st.title(f"🔥 {data['team_name']}")

    st.info(f"🎫 초대 코드: {st.session_state.invite_code} | 나: {st.session_state.my_name}")



    # 2. 팀원 슬롯 (서버 데이터 기반)

    cols = st.columns(10)

    for i, m in enumerate(data['members']):

        with cols[i]:

            is_active = "🔥" in m['status']

            color = "#FF4B4B" if is_active else "#eee"

            st.markdown(f"""

                <div style="border: 2px solid {color}; border-radius: 10px; padding: 10px; text-align: center;">

                    <b>{m['name']}</b><br>{m['status']}

                </div>

            """, unsafe_allow_html=True)



    st.divider()



    # 3. 실시간 상태 업데이트 함수

    def change_my_status(new_status):

        members = data['members']

        for m in members:

            if m['name'] == st.session_state.my_name:

                m['status'] = new_status

        supabase.table("teams").update({"members": members}).eq("invite_code", st.session_state.invite_code).execute()

        st.rerun()



    c1, c2 = st.columns(2)

    with c1:

        if st.button("🚀 공부 시작 (서버 전송)", use_container_width=True):

            change_my_status("🔥 공부중")

    with c2:

        if st.button("🏁 공부 종료 (서버 전송)", use_container_width=True):

            change_my_status("✅ 완료")



    if st.button("🔄 화면 새로고침 (친구 상태 확인)"):

        st.rerun()
