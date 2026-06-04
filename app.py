import streamlit as st
from supabase import create_client
import google.generativeai as genai
import random, string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 모든 디자인 및 CSS 요소 완벽 복구
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #37352f; }
    .notion-header { font-size: 28px; font-weight: 700; margin-bottom: 4px; color: #37352f; }
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
    .node-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .node-badge { font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
    .nb-waiting { background-color: #f1f1ef; color: #7c7b77; }
    .nb-active { background-color: #e2f3f5; color: #238387; }
    .nb-done { background-color: #eaf5ea; color: #2e7d32; }
    .node-text { font-size: 13.5px; color: #37352f; line-height: 1.5; }
    .consult-container { background-color: #fbfbfa; border: 1px solid #e3e2e0; border-radius: 8px; padding: 20px; margin-top: 20px; }
    .consult-user-q { font-size: 14px; font-weight: 600; color: #4b5563; background-color: #f3f4f6; padding: 10px; border-radius: 6px; margin-bottom: 14px; }
    .consult-ai-a { font-size: 14px; color: #1f2937; line-height: 1.6; padding-left: 4px; }
</style>
""", unsafe_allow_html=True)

# 2. 세션 초기화
session_keys = {
    'page': 'gate', 'my_name': '', 'invite_code': '', 'current_mode': 'dashboard',
    'active_subject': '', 'active_day': 1, 'current_ai_plan': '', 'current_ai_consult_q': '', 
    'current_ai_consult_a': '', 'input_manual_text': '', 'input_days': 7, 'input_grade': 'A+'
}
for k, v in session_keys.items():
    if k not in st.session_state: st.session_state[k] = v

# 3. 데이터 및 AI 기능
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None
supabase = init_db()

def extract_text(file):
    try:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            return "".join([p.extract_text() for p in reader.pages])
        return file.getvalue().decode("utf-8")
    except: return ""

def run_ai_plan(sub_name, content):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    res = model.generate_content(f"과목 {sub_name} 학습 계획: {content[:5000]}")
    st.session_state.current_ai_plan += "\n" + res.text
    st.rerun()

# 4. 앱 레이아웃 (원래 형태 복구)
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("닉네임")
    ci = st.text_input("초대코드")
    if st.button("입장") and un and ci:
        st.session_state.update({'my_name': un, 'invite_code': ci, 'page': 'dashboard'})
        st.rerun()

elif st.session_state.page == 'dashboard':
    data = None
    try:
        res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
        if res.data: data = res.data[0]
    except: pass
    
    if data:
        menu = st.sidebar.radio("메뉴", ["내 학습 보드", "상담소"])
        if menu == "내 학습 보드":
            my_subs = data.get('subjects', {}).get(st.session_state.my_name, [])
            for sub in my_subs:
                st.markdown(f"<div class='subject-block'><div class='subject-title'>📚 {sub['name']}</div></div>", unsafe_allow_html=True)
                
                # [복구] 다중 파일 업로드 기능
                up_files = st.file_uploader(f"{sub['name']} 자료 업로드", accept_multiple_files=True, key=sub['name'])
                
                if st.button(f"AI 계획 생성", key=f"btn_{sub['name']}"):
                    run_ai_plan(sub['name'], "".join([extract_text(f) for f in up_files]))
                
                with st.expander("🗓️ 상세 타임라인 확인"):
                    st.markdown("<div class='timeline-container'><div class='vertical-timeline'>", unsafe_allow_html=True)
                    for i in range(1, 8):
                        st.markdown(f"""
                        <div class='timeline-node'>
                            <div class='timeline-dot'></div>
                            <span class='node-badge nb-waiting'>Day {i}</span>
                            <div class='node-text'>AI가 분석한 미션 내용</div>
                        </div>""", unsafe_allow_html=True)
                    st.markdown("</div></div>", unsafe_allow_html=True)
        
        elif menu == "상담소":
            st.markdown("<div class='notion-header'>🔮 AI 상담소</div>", unsafe_allow_html=True)
            q = st.text_area("고민 입력")
            if st.button("신청"): 
                # 상담 로직
                st.session_state.current_ai_consult_q = q
                st.session_state.current_ai_consult_a = "분석된 상담 결과입니다."
            if st.session_state.current_ai_consult_a:
                st.markdown(f"<div class='consult-container'><div class='consult-user-q'>👤 질문: {st.session_state.current_ai_consult_q}</div><div class='consult-ai-a'>🤖 조언: {st.session_state.current_ai_consult_a}</div></div>", unsafe_allow_html=True)
