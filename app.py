import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader
import io

# --- 1. 서비스 연결 및 AI 초기화 (404/NotFound 완전 해결) ---
@st.cache_resource
def init_connection():
    try:
        s_url = st.secrets["SUPABASE_URL"]
        s_key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        
        # Supabase 연결
        s = create_client(s_url, s_key)
        
        # Gemini 설정
        genai.configure(api_key=g_key)
        
        # [핵심] 가장 범용적인 모델명부터 시도하며 '진짜' 연결되는지 확인
        selected_model = None
        for model_name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
            try:
                m = genai.GenerativeModel(model_name)
                # 실제로 핑을 날려 응답이 오는지 확인
                m.generate_content("hi", generation_config={"max_output_tokens": 1})
                selected_model = m
                break
            except Exception:
                continue
        
        return s, selected_model
    except Exception as e:
        st.error(f"🚨 시스템 초기 연결 실패: {e}")
        return None, None

supabase, model = init_connection()

# --- 2. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'gate'
if 'my_teams' not in st.session_state: st.session_state.my_teams = {}
if 'my_name' not in st.session_state: st.session_state.my_name = ""
if 'ai_ans' not in st.session_state: st.session_state.ai_ans = ""
if 'file_content' not in st.session_state: st.session_state.file_content = ""

# --- 3. 핵심 기능 함수 ---
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def run_ai(prompt_type, **kwargs):
    if not model:
        st.error("🤖 AI 모델이 연결되지 않았습니다. API 키나 모델 명칭을 다시 확인해주세요.")
        return
    
    with st.spinner("AI가 분석 중입니다..."):
        try:
            if prompt_type == "plan":
                p = f"성적목표:{kwargs['grade']}, 기간:{kwargs['days']}일. 다음 자료를 분석해 일정을 짜줘: {st.session_state.file_content[:4000]}"
            elif prompt_type == "quiz":
                p = f"다음 자료 기반 퀴즈 3개와 정답: {st.session_state.file_content[:4000]}"
            elif prompt_type == "consult":
                p = f"상담 답변 요청: {kwargs['q']}"
            
            res = model.generate_content(p)
            st.session_state.ai_ans = res.text
            st.rerun() # 답변이 나오면 즉시 화면 갱신
        except Exception as e:
            st.error(f"❌ AI 작동 오류: {str(e)}")

# --- 4. 메인 UI ---

if st.session_state.page == 'gate':
    st.title("🔥 Check-Mate")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🆕 팀 생성")
        tn = st.text_input("팀 이름", key="gate_tn")
        un = st.text_input("내 닉네임", key="gate_un")
        if st.button("팀 만들기"):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            supabase.table("team").insert({
                "invite_code": code, "team_name": tn,
                "members": [{"name": un, "status": "✅ 대기", "grade": "-", "days": "-"}],
                "subjects": {un: []}, "posts": []
            }).execute()
            st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"}); st.rerun()
    with c2:
        st.subheader("🔗 팀 참여")
        ci = st.text_input("초대 코드", key="gate_ci")
        ui = st.text_input("내 닉네임 ", key="gate_ui")
        if st.button("참여하기"):
            res = supabase.table("team").select("*").eq("invite_code", ci).execute()
            if res.data:
                d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                if not any(m['name'] == ui for m in ml):
                    ml.append({"name": ui, "status": "✅ 대기", "grade": "-", "days": "-"})
                    sl[ui] = []
                    supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                st.session_state.update({"invite_code": ci, "my_name": ui, "page": "dashboard"}); st.rerun()

elif st.session_state.page == 'dashboard':
    st_autorefresh(interval=30000, key="db_ref")
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        # [기능] 초대 코드 상시 노출
        st.sidebar.success(f"🎫 초대 코드: **{data['invite_code']}**")
        st.sidebar.title(f"🏫 {data['team_name']}")
        
        menu = st.sidebar.radio("메뉴", ["📚 내 학습 & AI", "👥 팀원 과목 상세", "📋 게시판", "💡 진로상담"])
        if st.sidebar.button("⬅️ 팀 나가기"): st.session_state.page = 'gate'; st.rerun()

        col_main, col_ai = st.columns([1, 1])

        with col_main:
            if menu == "📚 내 학습 & AI":
                st.header("📚 내 공부 관리")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                with st.expander("➕ 새 과목 등록"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 과목 선택", [s['name'] for s in my_subs])
                    up_file = st.file_uploader("자료 업로드(PDF/TXT)", type=['pdf', 'txt'])
                    if up_file:
                        st.session_state.file_content = extract_text(up_file)
                        st.success("✅ 파일 인식 완료")

                    st.divider()
                    c_d, c_g = st.columns(2)
                    with c_d: days = st.number_input("목표 기간(일)", 1, 100, 7)
                    with c_g: grade = st.selectbox("목표 성적", ["A+", "B+", "Pass"])
                    
                    if st.button("🪄 AI 맞춤 일정 생성", use_container_width=True):
                        if st.session_state.file_content:
                            # DB에 나의 목표 상태 공유
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name:
                                    m['grade'] = grade; m['days'] = f"{days}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai("plan", grade=grade, days=days)
                        else: st.warning("파일을 먼저 올려주세요.")

                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 공부 시작", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = f"🔥 {sel_sub} 중"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                    with c2:
                        if st.button("🏁 종료 & 퀴즈", use_container_width=True):
                            ml = data['members']
                            for m in ml:
                                if m['name'] == st.session_state.my_name: m['status'] = "✅ 대기"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            if st.session_state.file_content: run_ai("quiz")
                            st.rerun()

            elif menu == "👥 팀원 과목 상세":
                st.header("👥 팀원별 상세 과목 리스트")
                for m in data['members']:
                    with st.expander(f"{'🔥' if '중' in m['status'] else '✅'} {m['name']} 님의 현황"):
                        st.write(f"현재 상태: **{m['status']}**")
                        st.write(f"🎯 목표: **{m.get('grade', '-')}** | ⏳ 기간: **{m.get('days', '-')}**")
                        st.divider()
                        st.write("**📚 등록된 과목 목록**")
                        f_subs = data['subjects'].get(m['name'], [])
                        if f_subs:
                            for i, s in enumerate(f_subs):
                                st.info(f"{i+1}. {s['name']}")
                        else:
                            st.write("등록된 과목이 없습니다.")

            elif menu == "📋 게시판":
                st.header("📋 팀 공유 게시판")
                with st.form("b_form"):
                    bt, bc = st.text_input("제목"), st.text_area("내용")
                    if st.form_submit_button("등록"):
                        ps = data['posts']; ps.append({"title": bt, "content": bc, "author": st.session_state.my_name, "time": datetime.now().strftime("%H:%M")})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                for p in reversed(data['posts']):
                    with st.expander(f"{p['title']} - {p['author']}"): st.write(p['content'])

            elif menu == "💡 진로상담":
                st.header("💡 AI 상담소")
                q = st.text_area("고민 내용을 입력하세요.")
                if st.button("🔮 상담 시작"):
                    if q: run_ai("consult", q=q)

        with col_ai:
            st.header("🤖 AI Response")
            st.markdown("---")
            if st.session_state.ai_ans:
                st.markdown(st.session_state.ai_ans)
                if st.button("🧹 결과 지우기"):
                    st.session_state.ai_ans = ""
                    st.rerun()
            else:
                st.info("AI의 학습 플랜, 퀴즈 결과가 여기에 표시됩니다.")
