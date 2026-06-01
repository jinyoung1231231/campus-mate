import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# --- 스타일 리뉴얼 (CSS 주입) ---
st.markdown("""
<style>
    /* 전체 앱 배경 및 기본 글꼴 부드럽게 */
    .stApp {
        background-color: #f8f9fa;
    }
    /* 타이머 카드 디자인 */
    .timer-container {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    /* 일반 일정 카드 디자인 */
    .plan-card {
        background-color: white;
        border-left: 5px solid #cbd5e1;
        padding: 15px;
        border-radius: 4px 8px 8px 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        color: #334155;
    }
    /* 현재 진행 중인 하이라이트 일정 카드 디자인 */
    .active-plan-card {
        background-color: #fff7ed;
        border-left: 5px solid #f97316;
        padding: 18px;
        border-radius: 4px 8px 8px 4px;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15);
        margin-bottom: 15px;
        color: #431407;
    }
</style>
""", unsafe_allowed_allowed=True)

# 1. DB 연결
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 2. 세션 상태 관리 (입력 데이터 휘발 방지 로직 고도화)
session_keys = {
    'page': 'gate',
    'my_name': '',
    'invite_code': '',
    'timer_running': False,
    'start_time': None,
    'elapsed_time': 0,
    'current_ai_plan': '',
    'current_ai_quiz': '',
    'current_ai_consult': '',
    'input_manual_text': '', # 텍스트 입력값 보존용
    'input_days': 7,         # 기간 설정값 보존용
    'input_grade': 'A+'      # 목표 학점 보존용
}

for key, default in session_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 3. 파일 텍스트 추출 함수
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except:
        return ""

# 4. AI 핵심 구동 함수
def run_ai_engine(prompt_type, **kwargs):
    with st.spinner("AI가 분석 중입니다... 잠시만 기다려주세요. 📝"):
        try:
            today_str = datetime.now().strftime("%Y년 %m월 %d일")
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not valid_models:
                st.error("API 키 오류가 발생했습니다. 새 키를 설정해주세요.")
                return
            
            target_model = next((m for kw in ['flash-latest', '2.5-flash', '2.0-flash', '1.5-flash', 'flash'] for m in valid_models if kw in m and 'vision' not in m and 'lite' not in m), valid_models[0])
            model_instance = genai.GenerativeModel(target_model)

            if prompt_type == "plan":
                p = f"""오늘 날짜는 {today_str}입니다. 목표 성적: {kwargs['grade']}, 남은 기간: {kwargs['days']}일.
아래 제공된 학습 자료를 바탕으로, 각 일차별 학습 내용을 명확히 구분하여 작성해주세요.
반드시 각 일차의 시작은 'Day 1:', 'Day 2:' 와 같은 형식으로 작성해야 하며, 표를 만들지 말고 줄글 형식으로 작성하되 일차별 구분을 확실히 해주세요.

[학습 자료]
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.current_ai_plan = res.text
                st.session_state.current_ai_quiz = "" 
                
                # DB 영구 보존 데이터 동기화
                res_db = supabase.table("team").select("ai_plans").eq("invite_code", st.session_state.invite_code).execute()
                current_plans = res_db.data[0].get('ai_plans', {}) if res_db.data else {}
                if not current_plans: current_plans = {}
                current_plans[st.session_state.my_name] = res.text
                supabase.table("team").update({"ai_plans": current_plans}).eq("invite_code", st.session_state.invite_code).execute()

            elif prompt_type == "quiz":
                p = f"""아래 학습 자료를 바탕으로, 사용자의 목표 학점인 [{kwargs['grade']}] 수준에 맞는 핵심 복습 퀴즈 3개와 정답, 그리고 상세한 해설을 출제해주세요.
목표 학점이 A+인 경우 변별력 있는 심화 압박 질문을, B+ 이하인 경우 핵심 개념 위주의 방어형 질문을 출제해야 합니다.

[학습 자료]
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.current_ai_quiz = res.text

            elif prompt_type == "consult":
                p = f"학업 고민 및 상담 내용입니다: {kwargs['q']}\n학생의 상황에 공감하며 동기부여가 될 수 있는 체계적인 조언을 제공해주세요."
                res = model_instance.generate_content(p)
                st.session_state.current_ai_consult = res.text
            
            st.rerun()
                
        except Exception as e:
            st.error(f"AI 통신 중 오류가 발생했습니다: {e}")

# 5. 메인 화면 렌더링
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    st.write("닉네임을 입력해 내 팀을 확인하거나 새로 만드세요.")
    
    un = st.text_input("사용자 닉네임 (로그인)")
    
    if un:
        try:
            all_teams = supabase.table("team").select("*").execute().data
            my_teams = [t for t in all_teams if any(m['name'] == un for m in t['members'])]
            
            if my_teams:
                st.write("내 팀 목록")
                for t in my_teams:
                    if st.button(f"🏠 {t['team_name']} 입장", key=f"t_{t['invite_code']}"):
                        st.session_state.update({"invite_code": t['invite_code'], "my_name": un, "page": "dashboard"})
                        st.rerun()
            else:
                st.info("가입된 스터디 팀이 없습니다. 아래에서 팀을 생성하거나 초대 코드를 입력하세요.")
        except:
            st.warning("데이터베이스 연결을 확인하는 중입니다...")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("새 팀 만들기")
            tn = st.text_input("새 팀 이름")
            if st.button("방 만들기"):
                if tn and un:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    supabase.table("team").insert({
                        "invite_code": code, "team_name": tn,
                        "members": [{"name": un, "status": "대기", "grade": "-", "days": "-", "total_time": 0}],
                        "subjects": {un: []}, "posts": [], "ai_plans": {un: ""}
                    }).execute()
                    st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"})
                    st.rerun()
        with c2:
            st.write("초대 코드로 입장")
            ci = st.text_input("초대 코드")
            if st.button("팀 입장"):
                res = supabase.table("team").select("*").eq("invite_code", ci).execute()
                if res.data:
                    d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}; ap = d.get('ai_plans', {}) or {}
                    if not any(m['name'] == un for m in ml):
                        ml.append({"name": un, "status": "대기", "grade": "-", "days": "-", "total_time": 0})
                        sl[un] = []
                        if un not in ap: ap[un] = ""
                        supabase.table("team").update({"members": ml, "subjects": sl, "ai_plans": ap}).eq("invite_code", ci).execute()
                    st.session_state.update({"invite_code": ci, "my_name": un, "page": "dashboard"})
                    st.rerun()

elif st.session_state.page == 'dashboard':
    if not st.session_state.invite_code: 
        st.session_state.page = 'gate'; st.rerun()

    # 실시간 화면 동기화 및 타이머 초단위 갱신을 위한 주기 설정 (2초)
    st_autorefresh(interval=2000, key="global_refresh")
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        db_plans = data.get('ai_plans', {}) or {}
        if db_plans.get(st.session_state.my_name) and not st.session_state.current_ai_plan:
            st.session_state.current_ai_plan = db_plans.get(st.session_state.my_name)

        with st.sidebar.expander("초대코드 확인"):
            st.code(data['invite_code'])
        
        st.sidebar.title(f"{data['team_name']}")
        menu = st.sidebar.radio("메뉴", ["내 학습 & AI", "팀원 상세 과목", "게시판", "AI 상담소"])
        
        if st.sidebar.button("다른 팀으로 이동"):
            st.session_state.update({"invite_code": "", "page": "gate", "current_ai_plan": "", "current_ai_quiz": "", "current_ai_consult": ""})
            st.rerun()

        col_l, col_r = st.columns([1, 1])
        
        with col_l:
            if menu == "내 학습 & AI":
                st.header("내 공부 콘솔")
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                # --- 리뉴얼된 디지털 타이머 디자인 UI 적용 ---
                if st.session_state.timer_running:
                    current_elapsed = int(time.time() - st.session_state.start_time) + st.session_state.elapsed_time
                    h = current_elapsed // 3600; m = (current_elapsed % 3600) // 60; s = current_elapsed % 60
                    st.markdown(f"""<div class='timer-container'><div>⏳ 현재 실시간 몰입 시간</div><div style='font-size: 32px; font-weight: bold; margin-top: 5px;'>{h:02d}:{m:02d}:{s:02d}</div></div>""", unsafe_allowed_html=True)
                else:
                    h = st.session_state.elapsed_time // 3600; m = (st.session_state.elapsed_time % 3600) // 60; s = st.session_state.elapsed_time % 60
                    st.markdown(f"""<div class='timer-container' style='background: linear-gradient(135deg, #475569, #64748b);'><div>⏱️ 대기 중인 타이머</div><div style='font-size: 32px; font-weight: bold; margin-top: 5px;'>{h:02d}:{m:02d}:{s:02d}</div></div>""", unsafe_allowed_html=True)

                with st.expander("새 과목 추가"):
                    ns = st.text_input("과목명")
                    if st.button("등록"):
                        my_subs.append({"name": ns})
                        all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                        supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()

                if my_subs:
                    sel_sub = st.selectbox("현재 공부할 과목 선택", [s['name'] for s in my_subs])
                    st.divider()
                    
                    # [버그 수정] 세션 상태를 value와 연동하여 리프레시 시 입력값 유지
                    st.session_state.input_manual_text = st.text_area("자료 직접 입력 및 AI 지시사항 작성", value=st.session_state.input_manual_text, height=100)
                    up_file = st.file_uploader("교안 파일 업로드 (PDF/TXT)", type=['pdf', 'txt'])
                    
                    extracted = extract_text(up_file) if up_file else ""
                    if up_file and len(extracted) == 0:
                        st.warning("스캔된 PDF 문서입니다. 본문 텍스트를 위 입력창에 직접 붙여넣어 주세요.")
                    
                    combined_content = f"{st.session_state.input_manual_text}\n{extracted}".strip()
                    
                    c_d, c_g = st.columns(2)
                    # [버그 수정] 넘버인풋과 셀렉트박스도 세션을 보존하여 AI 통신 시 풀리지 않도록 조치
                    days = c_d.number_input("학습 기간 설정 (일)", 1, 100, value=st.session_state.input_days)
                    st.session_state.input_days = days
                    grade = c_g.selectbox("목표 성적 선택", ["A+", "B+", "Pass"], index=["A+", "B+", "Pass"].index(st.session_state.input_grade))
                    st.session_state.input_grade = grade
                    
                    if st.button("AI 맞춤 일정 새로 생성", type="primary", use_container_width=True):
                        if combined_content:
                            ml = data['members']
                            for m_block in ml:
                                if m_block['name'] == st.session_state.my_name: 
                                    m_block['grade'] = grade
                                    m_block['days'] = f"{days}일"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            run_ai_engine("plan", grade=grade, days=days, content=combined_content)
                        else:
                            st.warning("일정을 구성할 학습 자료나 지시사항을 입력해 주세요.")

                    st.divider()
                    
                    # 며칠차 할건지 선택하는 메뉴 동적 생성
                    selected_day = st.selectbox("오늘 진행할 목표 일차 선택", [f"Day {i}" for i in range(1, days + 1)])
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("공부 시작", use_container_width=True, disabled=st.session_state.timer_running):
                            st.session_state.timer_running = True
                            st.session_state.start_time = time.time()
                            ml = data['members']
                            for m_block in ml:
                                if m_block['name'] == st.session_state.my_name: 
                                    m_block['status'] = f"{sel_sub} ({selected_day}) 공부 중"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                    with c2:
                        if st.button("종료 및 퀴즈 풀기", use_container_width=True, disabled=not st.session_state.timer_running):
                            st.session_state.timer_running = False
                            gained_time = int(time.time() - st.session_state.start_time)
                            st.session_state.elapsed_time += gained_time
                            gained_minutes = gained_time // 60 if gained_time >= 60 else 1
                            
                            ml = data['members']
                            for m_block in ml:
                                if m_block['name'] == st.session_state.my_name: 
                                    m_block['status'] = "대기"
                                    m_block['total_time'] = m_block.get('total_time', 0) + gained_minutes
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            
                            target_user_grade = next((m_block.get('grade', 'B+') for m_block in data['members'] if m_block['name'] == st.session_state.my_name), 'B+')
                            run_ai_engine("quiz", grade=target_user_grade, content=combined_content if combined_content else "기본 학습 개념")

            elif menu == "팀원 상세 과목":
                st.header("팀원별 학습 현황")
                for m_block in data['members']:
                    with st.expander(f"{m_block['name']} 님"):
                        st.write(f"현재 상태: {m_block['status']}")
                        st.write(f"목표 성적: {m_block.get('grade', '-')} | 설정 기간: {m_block.get('days', '-')}")
                        st.write(f"오늘 누적 공부 시간: {m_block.get('total_time', 0)} 분")
                        st.write("등록된 모든 과목 목록")
                        f_subs = data['subjects'].get(m_block['name'], [])
                        for s in f_subs: st.info(s['name'])

            elif menu == "게시판":
                st.header("팀 공유 게시판")
                with st.form("b_form"):
                    t, c = st.text_input("글 제목"), st.text_area("글 내용")
                    if st.form_submit_button("게시글 등록"):
                        ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name})
                        supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                        st.rerun()
                
                # --- [기능 고도화] 게시글 삭제 시스템 구현 ---
                for idx, p in enumerate(reversed(data['posts'])):
                    real_idx = len(data['posts']) - 1 - idx
                    with st.expander(f"{p['title']} - 작성자: {p['author']}"):
                        st.write(p['content'])
                        # 본인이 작성한 글이거나 관리 권한 보장용 삭제 기능 조치
                        if p['author'] == st.session_state.my_name:
                            if st.button("🗑️ 이 게시글 삭제", key=f"del_{real_idx}"):
                                current_posts = data['posts']
                                current_posts.pop(real_idx)
                                supabase.table("team").update({"posts": current_posts}).eq("invite_code", st.session_state.invite_code).execute()
                                st.rerun()

            elif menu == "AI 상담소":
                st.header("AI 1:1 상담소")
                user_query = st.text_area("학업 고민이나 슬럼프에 대해 자유롭게 적어주세요.", height=150)
                if st.button("멘토에게 조언 구하기", type="primary"):
                    if user_query:
                        run_ai_engine("consult", q=user_query)

        # 우측 결과단 영역
        with col_r:
            if menu in ["내 학습 & AI", "팀원 상세 과목", "게시판"]:
                st.header("🤖 AI 학습 일정 검증 센터")
                st.divider()
                
                if st.session_state.current_ai_plan:
                    st.write("📋 **나의 맞춤형 일차별 계획**")
                    
                    lines = st.session_state.current_ai_plan.split('\n')
                    for line in lines:
                        if not line.strip(): continue
                        
                        # --- [디자인 리뉴얼] 가독성을 위해 개별 카드 컴포넌트로 변경 및 하이라이트 구현 ---
                        if menu == "내 학습 & AI" and selected_day in line:
                            # 현재 선택된 Day는 강조된 오렌지색 카드로 연출
                            st.markdown(f"""<div class='active-plan-card'>{line}</div>""", unsafe_allowed_html=True)
                        else:
                            # 나머지 날짜는 깔끔한 슬레이트 화이트 카드로 정돈
                            st.markdown(f"""<div class='plan-card'>{line}</div>""", unsafe_allowed_html=True)
                else:
                    st.info("좌측 콘솔에서 자료 입력 후 AI 맞춤 일정을 생성하면 여기에 영구 보존됩니다.")
                
                if st.session_state.current_ai_quiz:
                    st.divider()
                    st.subheader("📝 목표 성적 맞춤형 실전 검증 퀴즈")
                    st.write(st.session_state.current_ai_quiz)

            elif menu == "AI 상담소":
                st.header("🔮 AI 마인드셋 상담 피드백")
                st.divider()
                if st.session_state.current_ai_consult:
                    st.write(st.session_state.current_ai_consult)
                else:
                    st.info("좌측 상담소에 고민을 입력하시면 AI 멘토의 따뜻한 1:1 솔루션이 이곳에 단독으로 제공됩니다.")
