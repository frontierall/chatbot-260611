import hashlib
import io
import json

import streamlit as st
from audio_recorder_streamlit import audio_recorder
from openai import OpenAI

st.title("💬 Chatbot")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")

    openai_api_key = st.text_input("OpenAI API Key", type="password")

    model = st.selectbox(
        "Model",
        options=["gpt-5.4-mini", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=0,
        help="gpt-5.4-mini: 최신/빠름 | gpt-4o-mini: 성능/가격 균형 | gpt-4o: 고성능 | gpt-3.5-turbo: 구형",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
        help="낮을수록 일관된 답변, 높을수록 창의적인 답변",
    )

    st.divider()
    st.subheader("Export Chat")

    if st.session_state.get("messages"):
        # TXT export
        txt_lines = "\n".join(
            f"[{m['role'].upper()}]\n{m['content']}\n"
            for m in st.session_state.messages
        )
        st.download_button(
            label="Download as .txt",
            data=txt_lines,
            file_name="chat_history.txt",
            mime="text/plain",
        )

        # JSON export
        json_data = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
        st.download_button(
            label="Download as .json",
            data=json_data,
            file_name="chat_history.json",
            mime="application/json",
        )

        if st.button("Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.rerun()
    else:
        st.caption("대화를 시작하면 내보내기가 활성화됩니다.")

# ── Main ──────────────────────────────────────────────────────────────────────
if not openai_api_key:
    st.info("사이드바에 OpenAI API 키를 입력하면 대화를 시작할 수 있습니다.", icon="🗝️")
    st.stop()

client = OpenAI(api_key=openai_api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Voice input — click to record, click again (or 2s silence) to stop
st.write("🎤 음성 입력 (버튼 클릭 후 말하기):")
audio_bytes = audio_recorder(pause_threshold=2.0, sample_rate=41_000)

voice_prompt = None
if audio_bytes:
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    if audio_hash != st.session_state.last_audio_hash:
        st.session_state.last_audio_hash = audio_hash
        with st.spinner("음성 인식 중..."):
            try:
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "audio.wav"
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko",
                )
                voice_prompt = transcript.text
                if voice_prompt:
                    st.info(f"인식된 텍스트: **{voice_prompt}**")
            except Exception as e:
                st.error(f"음성 인식 실패: {e}")

text_prompt = st.chat_input("메시지를 입력하거나 위의 🎤 버튼으로 말하세요")
prompt = voice_prompt or text_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            temperature=temperature,
            stream=True,
        )
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
    except Exception as e:
        st.error(f"응답 생성 실패: {e}")
