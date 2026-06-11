# 💬 Chatbot

OpenAI API를 사용하는 Streamlit 챗봇 앱입니다.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

## 기능

- **모델 선택** — `gpt-5.4-mini` (기본) / `gpt-4o-mini` / `gpt-4o` / `gpt-3.5-turbo` 드롭다운 선택
- **Temperature 조절** — 0.0 ~ 2.0 슬라이더로 응답 창의성 제어
- **스트리밍 응답** — 답변이 실시간으로 출력됨
- **멀티턴 대화** — 전체 대화 히스토리를 유지해 문맥 있는 대화 지원
- **채팅 내보내기** — 대화 내용을 `.txt` 또는 `.json`으로 다운로드
- **대화 초기화** — Clear Chat 버튼으로 세션 초기화

## 실행 방법

1. 의존성 설치

   ```
   pip install -r requirements.txt
   ```

2. 앱 실행

   ```
   streamlit run streamlit_app.py
   ```

3. 사이드바에 [OpenAI API 키](https://platform.openai.com/account/api-keys)를 입력하면 바로 사용 가능합니다.
