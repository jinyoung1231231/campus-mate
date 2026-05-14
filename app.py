import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string

# 1. 연결 설정 (슬래시 / 주의!!)
URL = "https://bpyxibaquftjjzvsoord.supabase.co" # 주소 끝에 아무것도 붙이지 마세요
KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

# 서버 연결 (예외처리 추가)
try:
    supabase: Client = create_client(URL, KEY)
    genai.configure(api_key=GEMINI)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"연결 실패: {e}")

if 'page' not in st.session_state: st.session_state.page = 'gate'

# --- 게이트웨이 ---
if st.session_state.page == 'gate':
    st.title("🔥 체크메이트")
    if st.button("팀 만들기"): st.session_state.page = 'create'; st.rerun()
    if st.button("참여하기"): st.session_state.page = 'join'; st.rerun()

# --- 팀 생성 로직 (수정본) ---
elif st.session_state.page == 'create':
    st.subheader("🆕 새로운 팀 만들기")
    t_name = st.text_input("팀 이름", placeholder="예: 파이썬 열공방")
    u_name = st.text_input("내 닉네임", placeholder="예: 홍길동")
    
    if st.button("확인 및 시작"):
        if not t_name or not u_name:
            st.warning("이름과 닉네임을 모두 입력해주세요!")
        else:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            row = {
                "invite_code": code,
                "team_name": t_name,
                "members": [{"name": u_name, "status": "대기"}],
                "subjects": {"기본과목": {"grade": "A+"}} # 초기 과목 설정
            }
            
            try:
                # 1. 서버 저장
                supabase.table("team").insert(row).execute()
                
                # 2. 세션 상태에 저장 (이게 중요!)
                st.session_state.invite_code = code
                st.session_state.my_name = u_name
               # --- 화면 3: 대시보드 (데이터 로딩 강화) ---
elif st.session_state.page == 'dashboard':
    # 서버에서 최신 데이터 가져오기
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    
    if not res.data:
        st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.")
        if st.button("처음으로 돌아가기"):
            st.session_state.page = 'gate'
            st.rerun()
        st.stop()

    data = res.data[0]
    
    # 만약 subjects가 비어있다면 기본값 설정
    subjects = data.get('subjects') or {"기본": {"grade": "A+"}}
    members = data.get('members') or []

    st.title(f"🔥 {data.get('team_name', '우리 팀')}")
    st.info(f"🎫 초대 코드: **{st.session_state.invite_code}** | 내 닉네임: **{st.session_state.my_name}**")

    # 1. 팀원 현황 (실시간)
    st.subheader("👥 팀원 상태")
    cols = st.columns(len(members) if len(members) > 0 else 1)
    for i, m in enumerate(members):
        with cols[i % len(cols)]:
            st.markdown(f"""
                <div style="border: 2px solid #ddd; border-radius: 10px; padding: 10px; text-align: center;">
                    <b>{m['name']}</b><br>{m['status']}
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 2. 과목별 공부 & AI 퀴즈
    if subjects:
        tabs = st.tabs(list(subjects.keys()))
        for i, tab in enumerate(tabs):
            s_name = list(subjects.keys())[i]
            with tab:
                st.subheader(f"📚 {s_name}")
                up_file = st.file_uploader(f"{s_name} 자료 업로드", key=f"file_{s_name}")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"🚀 {s_name} 공부 시작", key=f"start_{s_name}"):
                        # 상태 업데이트 함수 호출 (기존 함수 그대로 사용)
                        update_db_status(f"🔥 {s_name} 공부중")
                        st.rerun()
                with c2:
                    if st.button(f"🏁 종료 및 퀴즈", key=f"end_{s_name}"):
                        update_db_status("✅ 완료")
                        if up_file:
                            st.success("AI 퀴즈 생성 중... (Gemini 호출)")
                            # Gemini 코드 부분...
                        else:
                            st.warning("파일을 올려주세요!")

    if st.button("🔄 화면 새로고침"):
        st.rerun()
