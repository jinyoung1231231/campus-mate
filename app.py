import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random, string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 노션 스타일 및 수직선 타임라인 전용 CSS (모든 디테일 복구)
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #37352f; }
    .notion-header { font-size: 28px; font-weight: 700; margin-bottom: 4px; color: #37352f; }
    .notion-sub { font-size: 14px; color: #7c7b77; margin-bottom: 24px; }
    .subject-block { background-color: #fbfbfa; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
    .subject-title { font-size: 18px; font-weight: 700; color: #37352f; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
    .schedule-box { background-color: #f7f7f5; border-radius: 6px; padding: 12px 16px; margin-top: 12px; margin-bottom: 16px; border-left: 3px solid #60a5fa; display: flex; gap: 24px; }
    .schedule-item { font-size: 13px; color: #4b5563; }
    .timeline-container { background-color: #ffffff; border: 1px solid #ededeb; border-radius: 8px; padding: 20px; margin-top: 14px; }
    .vertical-timeline { border-left: 2px solid #e3e2e0; margin-left: 12px; padding-left: 24px; margin-top: 16px; }
    .timeline-node { position: relative; margin-bottom: 18px; }
    .timeline-dot { position: absolute; left: -31px; top: 3px; width: 12px; height: 12px; border-radius: 50%; background-color: #fff; border: 3px solid #cbd5e1; z-index: 2; }
    .dot-active { border-color: #238387; background-color: #238387; box-shadow: 0 0 0 4px #e2f3f5; }
    .dot-done { border-color: #2e7d32; background-color: #2e7d32; }
    .node-badge { font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
    .nb-waiting { background-color: #f1f1ef; color: #7c7b77; }
    .nb-active { background-color: #e2f3f5; color: #238387; }
    .nb-done { background-color: #eaf5ea; color: #2e7d32; }
    .consult-container { background-color: #fbfbfa; border: 1px solid #e3e2e0; border-radius: 8px; padding: 20px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# 2. 초기화 및 데이터 로딩 방어 로직
session_keys = {
    'page': 'gate', 'my_name': '', 'invite_code': '', 'current_mode': 'dashboard',
    'active_subject': '', 'active_day': 1, 'current_ai_plan': '', 'current_ai_consult_q': '',
    'current_ai_consult_a': '', 'input_manual_text': '', 'input_days': 7, 'input_grade': 'A+'
}
for k, v in session_keys.items():
    if k not in st.session_state: st.session_state[k] = v

@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None
supabase = init_db()

data = None
if st.session_state.invite_code:
    try:
        res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
        if res.data: data = res.data[0]
    except: pass

# 3. 파일 파싱 및 AI 기능
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except: return ""

def run_ai_engine(prompt_type, **kwargs):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if prompt_type == "plan":
        p = f"과목 {kwargs['sub_name']}의 {kwargs['days']}일 학습 계획을 짜줘. 형식: '과목명 Day 숫자: 내용'. 내용: {kwargs['content'][:5000]}"
        res = model.generate_content(p)
        st.session_state.current_ai_plan += "\n" + res.text
    elif prompt_type == "consult":
        st.session_state.current_ai_consult_q = kwargs['q']
        st.session_state.current_ai_consult_a = model.generate_content(f"학업 상담: {kwargs['q']}").text
    st.rerun()

# 4. 앱 레이아웃
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임")
    ci = st.text_input("초대코드")
    if st.button("입장") and un and ci:
        st.session_state.update({'my_name': un, 'invite_code': ci, 'page': 'dashboard'})
        st.rerun()

elif st.session_state.page == 'dashboard' and data:
    menu = st.sidebar.radio("메뉴", ["내 학습 보드", "상담소"])
    
    if menu == "내 학습 보드":
        my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
        for sub in my_subs:
            # 과목별 1단 세로 정렬 카드
            st.markdown(f"<div class='subject-block'><div class='subject-title'>📚 {sub['name']}</div></div>", unsafe_allow_html=True)
            
            # 다중 파일 업로드
            up_files = st.file_uploader(f"{sub['name']} 자료 업로드", accept_multiple_files=True, key=sub['name'])
            if st.button(f"계획 생성", key=f"btn_{sub['name']}"):
                run_ai_engine("plan", sub_name=sub['name'], content="".join([extract_text(f) for f in up_files]), grade="A+", days=7)
            
            # 수직선 타임라인 보드
            with st.expander("🗓️ 상세 타임라인 보기", expanded=True):
                st.markdown("<div class='timeline-container'><div class='vertical-timeline'>", unsafe_allow_html=True)
                for i in range(1, 8):
                    st.markdown(f"""
                    <div class='timeline-node'>
                        <div class='timeline-dot'></div>
                        <span class='node-badge nb-waiting'>Day {i}</span>
                        <div class='node-text'>학습 미션 내용 예시</div>
                    </div>""", unsafe_allow_html=True)
                st.markdown("</div></div>", unsafe_allow_html=True)

    elif menu == "상담소":
        st.markdown("<div class='notion-header'>🔮 AI 상담소</div>", unsafe_allow_html=True)
        q = st.text_area("고민 입력")
        if st.button("신청"): run_ai_engine("consult", q=q)
        # 상담 답변 하단 고정
        if st.session_state.current_ai_consult_a:
            st.markdown(f"<div class='consult-container'><b>질문:</b> {st.session_state.current_ai_consult_q}<br><br><b>답변:</b> {st.session_state.current_ai_consult_a}</div>", unsafe_allow_html=True)
