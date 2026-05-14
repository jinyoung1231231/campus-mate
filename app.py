import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 보안 설정 ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Secrets 설정 확인 필요: SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY")
    st.stop()

@st.cache_resource
def init_connection():
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    m = None
    # 모델명을 순차적으로 시도 (가장 호환성 높은 방식)
    for model_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            temp_model = genai.GenerativeModel(model_name)
            temp_model.generate_content("hi", generation_config={"max_output_tokens": 1})
            m = temp_model
            break
        except: continue
    return s, m

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"연결 실패: {e}")

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_teams' not in st.session_state:
    st.session_state.my_teams = {}
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""
# 상담 결과 저장을 위한 세션 추가
if 'career_result' not in st.session_state:
    st.session_state.career_result = None

def get_team_data(code):
    res = supabase.table("team").select("*").eq("invite_code", code).execute()
    return res.data[0] if res.data else None

def update_db_status(code, name, status):
    data = get_team_data(code)
    if data:
        m_list = data['members']
        for m in m_list:
            if m['name'] == name: m['status'] = status
        supabase.table("team").update({"members": m_list}).eq("invite_code", code).execute()

def update_db_subjects(code, name, subs):
    data = get_team_data(code)
    if data:
        all_subs = data.get('subjects', {})
        all_subs[name] = subs
        supabase.table("team").update({"subjects": all_subs}).eq("invite_code", code).execute()

# --- 3. 화면 로직 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 나의 스터디 팀")
        for code, t_name in st.session_state.my_teams.items():
            if st.button(f"🏫 {t_name} ({code})", key=f"go_{code}", use_container_width=True):
                st.session_state.invite_code = code
                st.session_state.page = 'dashboard'; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성"): st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여"): st.session_state.page = 'join'; st.rerun()

elif st.session_state.page == 'create':
    st.title("🆕 팀 만들기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("생성 완료"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": t_name,
                "members": [{"name": u_name, "status": "✅ 대기"}],
                "subjects": {u_name: ["자유 공부"]}
            }).execute()
            st.session_state.my_teams[code] = t_name
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

elif st.session_state.page == 'dashboard':
    # [수정] 자동 갱신 주기를 5초 -> 15초로 늘려 상담 시간이 끊기지 않게 함
    st_autorefresh(interval=15000, key="refresh")
    
    data = get_team_data(st.session_state.invite_code)
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.sidebar.button("⬅️ 목록으로", on_click=lambda: st.session_state.update({"page": "gate"}))
        
        # 팀원 현황
        st.subheader("👥 팀원 현황")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                st.info(f"**{m['name']}**\n\n{m['status']}")
        
        st.divider()
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["자유 공부"])
        
        st.subheader(f"📚 {my_name}님의 학습실")
        # (과목 관리 로직 생략 없이 그대로 유지)
        new_s = st.text_input("과목 추가", placeholder="새 과목 입력")
        if st.button("➕ 추가"):
            if new_s and new_s not in my_subs:
                my_subs.append(new_s); update_db_subjects(st.session_state.invite_code, my_name, my_subs); st.rerun()
        
        if my_subs:
            tabs = st.tabs(my_subs)
            for i, tab in enumerate(tabs):
                s_name = my_subs[i]
                with tab:
                    if st.button(f"❌ {s_name} 삭제", key=f"del_{s_name}"):
                        my_subs.remove(s_name); update_db_subjects(st.session_state.invite_code, my_name, my_subs); st.rerun()
                    up_file = st.file_uploader(f"자료 업로드", key=f"f_{s_name}")
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button(f"🚀 시작", key=f"st_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, f"🔥 {s_name} 중"); st.rerun()
                    with cb2:
                        if st.button(f"🏁 퀴즈", key=f"ed_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, "✅ 대기")
                            if up_file and model:
                                with st.spinner("AI 퀴즈 생성 중..."):
                                    resp = model.generate_content(f"{s_name}에 대한 퀴즈 3개 내줘.")
                                    st.session_state.last_quiz = resp.text
                                    st.rerun()

        st.divider()
        # [수정] AI 진로 상담소 - 세션 저장 방식 적용
        st.subheader("💡 AI 진로 상담소")
        career_q = st.text_area("진로 고민을 적어주세요 (예: 전공과 취업 방향)")
        
        if st.button("🔮 상담 시작", use_container_width=True):
            if career_q:
                if model:
                    with st.spinner("AI 상담사가 분석 중입니다..."):
                        try:
                            # AI 답변 생성
                            resp = model.generate_content(f"커리어 상담가로서 친절하게 조언해줘: {career_q}")
                            st.session_state.career_result = resp.text
                        except Exception as e:
                            st.error(f"상담 중 오류 발생: {e}")
                else:
                    st.error("AI 모델 연결 실패. Secrets 설정을 확인하세요.")
            else:
                st.warning("고민 내용을 입력해주세요.")

        # 상담 결과가 세션에 있으면 출력
        if st.session_state.career_result:
            st.info("🤖 AI 상담 결과")
            st.write(st.session_state.career_result)
            if st.button("결과 닫기"):
                st.session_state.career_result = None
                st.rerun()
