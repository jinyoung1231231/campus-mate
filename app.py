elif prompt_type == "quiz_questions":
                p = f"""당신은 대학교 교수이자 시험 출제위원입니다. 
아래 [학습 자료]만을 읽고, 주관식/서술형 퀴즈 3개와 그에 대한 정답을 함께 출제하세요.

작성 수칙 - 매우 중요
1. 문제 1, 2는 단답형, 문제 3은 서술형입니다.
2. 반드시 아래 [출제 양식]을 그대로 따르고, 문제와 정답 사이에 '정답선' 이라는 단어를 무조건 넣어야 합니다.
3. 별표 마크다운 효과를 전혀 쓰지 말고 순수 텍스트로만 작성하세요.

[출제 양식]
문제 1. (문제 내용)

문제 2. (문제 내용)

문제 3. (문제 내용)

정답선
[정답 및 해설]
1번 정답: 
2번 정답: 
3번 정답/해설: 

학습 자료
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                
                # 수정된 파싱 로직: 기호에 얽매이지 않고 유연하게 자릅니다.
                if "정답선" in res.text:
                    parts = res.text.split("정답선", 1)
                    st.session_state.current_ai_quiz = parts[0].strip("= -\n")
                    st.session_state.current_ai_quiz_answers = parts[1].strip("= -\n")
                else:
                    st.session_state.current_ai_quiz = res.text.strip()
                    st.session_state.current_ai_quiz_answers = "AI가 해설을 분리하지 못했습니다. 채점 시 전체 문항을 참고해주세요."
