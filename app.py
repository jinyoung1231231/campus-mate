import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string

# --- 1. 설정 (본인의 키를 꼭 넣어주세요) ---
SUPABASE_URL = "https://bpyxibaquftjjzvsoord.supabase.co"
SUPABASE_KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI_API_KEY = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49OyoAIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

# 서비스 연결
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("연결 설정에 문제가 있습니다. URL과 Key를 확인해주세요.")

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'

# --- [함수] 서버 데이터 업데이트 (테이블 이름 'team'으로 수정됨) ---
def update_db_status(new_status):
    # 'team' 테이블에서 데이터를 가져옵니다.
    res = supabase.table("team").select("members").eq("invite_code", st.session_state.invite_code).execute()
    if res.data:
        members = res.data[0]['members']
        for m in members:
            if m['name'] == st.session_state.my_name:
                m['status'] = new_status
        # 'team' 테이블의 데이터를 업데이트합니다.
        supabase.table("team").update({"members": members}).eq("invite_code", st.session_state.invite_code).execute()

# --- 화면 0: 게이트웨이 ---
if st.session_state.page == 'gate':
    st.title("🚀 Check-Mate: AI 멀티 캠퍼스")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True): 
            st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 초대코드로 합류", use_container_width=True): 
            st.session_state.page = 'join'; st.rerun()

# --- 화면 1: 팀 생성 (테이블 이름 'team' 사용) ---
elif st.session_state.page == 'create':
    with st.form("c_form"):
        t_name = st.text_input("팀 이름")
        my_nick = st.text_input("내 닉네임")
        sub_input = st.text_input("과목들을 쉼표로 구분 (예: 파이썬, 수학)")
        if st.form_submit_button("팀 만들기"):
            if t_name and my_nick and sub_input:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                sub_list = [s.strip() for s in sub_input.split(",") if s.strip()]
                subs_data = {s: {"grade": "A+", "files": []} for s in sub_list}
                
                # 'team' 테이블에 저장
                supabase.table("team").insert({
                    "invite_code": code, 
                    "team_name": t_name, 
                    "members": [{"name": my_nick, "status": "✅ 대기"}],
                    "subjects": subs_data
                }).execute()
                
                st.session_state.update({"invite_code": code, "my_name": my_nick, "page": "dashboard"})
                st.rerun()

# --- 화면 2: 합류하기 (테이블 이름 'team' 사용) ---
elif st.session_state.page == 'join':
    code_in = st.text_input("초대 코드 6자리").upper()
    nick_in = st.text_input("내 닉네임")
    if st.button("입장하기"):
        res = supabase.table("team").select("*").eq("invite_code", code_in).execute()
        if res.data:
            m = res.data[0]['members']
            if not any(x['name'] == nick_in for x in m):
                m.append({"name": nick_in, "status": "✅ 대기"})
                supabase.table("team").update({"members": m}).eq("invite_code", code_in).execute()
            st.session_state.update({"invite_code": code_in, "my_name": nick_in, "page": "dashboard"})
            st.rerun()
        else:
            st.error("코드를 찾을 수 없습니다.")

# --- 화면 3: 대시보드 및 AI 기능 ---
elif st.session_state.page == 'dashboard':
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    if not res.data: st.stop()
    data = res.data[0]
    
    st.title(f"🔥 {data['team_name']}")
    st.info(f"🎫 코드: {st.session_state.invite_code} | 사용자: {st.session_state.my_name}")

    # 팀원 현황
    cols = st.columns(5)
    for i, m in enumerate(data['members']):
        with cols[i % 5]:
            st.markdown(f"<div style='text-align:center; padding:10px; border:1px solid #ddd;'><b>{m['name']}</b><br>{m['status']}</div>", unsafe_allow_html=True)

    st.divider()

    # 과목별 공부 & AI 퀴즈
    tabs = st.tabs(list(data['subjects'].keys()))
    for i, tab in enumerate(tabs):
        s_name = list(data['subjects'].keys())[i]
        with tab:
            st.subheader(f"📚 {s_name}")
            up_file = st.file_uploader(f"학습 자료(PDF/이미지)", key=f"f_{s_name}")
            
            if st.button(f"🚀 {s_name} 공부 시작", key=f"start_{s_name}"):
                update_db_status(f"🔥 {s_name} 열공중")
                st.rerun()
            
            if st.button(f"🏁 공부 종료 & AI 퀴즈", key=f"end_{s_name}"):
                update_db_status("✅ 완료")
                if up_file:
                    with st.spinner("AI가 문제를 출제하고 있습니다..."):
                        # Gemini AI 호출
                        prompt = f"이 자료를 바탕으로 공부를 마친 학생에게 낼 아주 중요한 퀴즈 3개만 내줘."
                        response = model.generate_content([prompt, up_file.name])
                        st.success("🤖 AI가 뽑은 오늘의 핵심 퀴즈!")
                        st.write(response.text)
                else:
                    st.warning("파일을 먼저 업로드해야 AI가 퀴즈를 낼 수 있습니다!")

    if st.button("🔄 전체 상태 새로고침"): st.rerun()
