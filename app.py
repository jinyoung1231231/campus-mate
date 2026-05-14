import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. 보안 설정 및 연결 ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Secrets 설정 확인 필요 (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY)")
    st.stop()

@st.cache_resource
def init_connection():
    s = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    m = None
    for name in ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']:
        try:
            temp_model = genai.GenerativeModel(name)
            temp_model.generate_content("hi", generation_config={"max_output_tokens": 1})
            m = temp_model
            break
        except: continue
    return s, m

try:
    supabase, model = init_connection()
except Exception as e:
    st.error(f"❌ 서비스 연결 실패: {e}")

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state:
    st.session_state.page = 'gate'
if 'my_teams' not in st.session_state:
    st.session_state.my_teams = {}
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""
if 'career_result' not in st.session_state: # 상담 결과 저장소
    st.session_state.career_result = None

def get_team_data(code):
    try:
        res = supabase.table("team").select("*").eq("invite_code", code).execute()
        return res.data[0] if res.data else None
    except: return None

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

# --- 3. 화면 UI 로직 ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    if st.session_state.my_teams:
        st.subheader("🏠 나의 팀 리스트")
        for code, t_name in st.session_state.my_teams.items():
            col_t, col_b = st.columns([4, 1])
            with col_t:
                if st.button(f"🏫 {t_name} [코드: {code}]", key=f"go_{code}", use_container_width=True):
                    st.session_state.invite_code = code
                    st.session_state.page = 'dashboard'; st.rerun()
            with col_b:
                if st.button("❌", key=f"out_{code}"):
                    del st.session_state.my_teams[code]; st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 팀 생성", use_container_width=True): st.session_state.page = 'create'; st.rerun()
    with c2:
        if st.button("🔗 팀 참여", use_container_width=True): st.session_state.page = 'join'; st.rerun()

elif st.session_state.page == 'create':
    st.title("🆕 새로운 팀 만들기")
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("팀 생성 및 입장"):
        if t_name and u_name:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": t_name,
                "members": [{"name": u_name, "status": "✅ 대기 중"}],
                "subjects": {u_name: ["자유 공부"]}
            }).execute()
            st.session_state.my_teams[code] = t_name
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()

elif st.session_state.page == 'join':
    st.title("🔗 팀 참여하기")
    code_in = st.text_input("초대 코드 6자리").upper()
    u_name = st.text_input("내 닉네임")
    if st.button("참여하기"):
        data = get_team_data(code_in)
        if data:
            m_list = data['members']
            all_subs = data.get('subjects', {})
            if not any(m['name'] == u_name for m in m_list):
                m_list.append({"name": u_name, "status": "✅ 대기 중"})
                if u_name not in all_subs: all_subs[u_name] = ["자유 공부"]
                supabase.table("team").update({"members": m_list, "subjects": all_subs}).eq("invite_code", code_in).execute()
            st.session_state.my_teams[code_in] = data['team_name']
            st.session_state.update({"invite_code": code_in, "my_name": u_name, "page": "dashboard"})
            st.rerun()
        else: st.error("코드가 올바르지 않습니다.")

elif st.session_state.page == 'dashboard':
    # [중요] 상담 중 끊김 방지를 위해 자동 갱신을 30초로 연장
    st_autorefresh(interval=30000, key="refresh")
    
    data = get_team_data(st.session_state.invite_code)
    if data:
        st.title(f"🏫 {data['team_name']}")
        st.error(f"📢 초대 코드: **{st.session_state.invite_code}**")
        st.sidebar.button("⬅️ 팀 목록으로", on_click=lambda: st.session_state.update({"page": "gate"}))
        
        st.subheader("👥 팀원 현황")
        m_cols = st.columns(5)
        for i, m in enumerate(data['members']):
            with m_cols[i % 5]:
                st.info(f"**{m['name']}**\n\n{m['status']}")
        
        st.divider()
        my_name = st.session_state.my_name
        my_subs = data.get('subjects', {}).get(my_name, ["자유 공부"])
        
        st.subheader(f"📚 {my_name}님의 학습실")
        new_s = st.text_input("과목 추가", placeholder="과목 이름 입력", label_visibility="collapsed")
        if st.button("➕ 과목 추가"):
            if new_s and new_s not in my_subs:
                my_subs.append(new_s); update_db_subjects(st.session_state.invite_code, my_name, my_subs); st.rerun()
        
        if my_subs:
            tabs = st.tabs(my_subs)
            for i, tab in enumerate(tabs):
                s_name = my_subs[i]
                with tab:
                    col_t, col_d = st.columns([4, 1])
                    with col_t: st.write(f"📖 **{s_name}**")
                    with col_d:
                        if st.button("❌", key=f"del_{s_name}"):
                            my_subs.remove(s_name); update_db_subjects(st.session_state.invite_code, my_name, my_subs); st.rerun()
                    
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if st.button(f"🚀 시작", key=f"st_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, f"🔥 {s_name} 중"); st.rerun()
                    with cb2:
                        if st.button(f"🏁 퀴즈", key=f"ed_{s_name}", use_container_width=True):
                            update_db_status(st.session_state.invite_code, my_name, "✅ 대기 중"); st.rerun()

        st.divider()
        
        # --- [핵심 수정] 상담소 로직 ---
        st.subheader("💡 AI 진로 상담소")
        # 1. 입력창 (세션 상태에 고정하기 위해 폼 사용 안 함)
        career_input = st.text_area("진로 고민을 적어주세요", key="career_text_area")
        
        # 2. 버튼
        if st.button("🔮 상담 시작", use_container_width=True):
            if career_input:
                if model:
                    with st.spinner("AI 상담사가 분석 중입니다. 잠시만 기다려주세요..."):
                        try:
                            # AI 답변 생성
                            resp = model.generate_content(f"커리어 상담가로서 다음 고민에 대해 친절하고 구체적으로 조언해줘: {career_input}")
                            # 결과를 세션에 저장 (새로고침되어도 남도록)
                            st.session_state.career_result = resp.text
                            st.rerun() # 결과 보여주기 위해 새로고침
                        except Exception as e:
                            st.error(f"상담 오류: {e}")
                else:
                    st.error("AI 모델 연결 실패. Secrets 설정을 확인하세요.")
            else:
                st.warning("고민 내용을 입력해주세요.")

        # 3. 결과 표시 (세션에 결과가 있을 때만)
        if st.session_state.career_result:
            st.success("🤖 AI 상담 결과")
            st.markdown(st.session_state.career_result)
            if st.button("상담 결과 닫기"):
                st.session_state.career_result = None
                st.rerun()
