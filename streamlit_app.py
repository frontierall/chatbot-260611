import hashlib
import io
import json

import pandas as pd
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

    st.divider()
    st.subheader("데이터 분석")
    uploaded_file = st.file_uploader(
        "CSV 또는 Excel 파일 업로드",
        type=["csv", "xlsx", "xls"],
        help="파일을 업로드하면 챗봇이 데이터를 인식하고 분석해 드립니다.",
    )
    if uploaded_file:
        try:
            df, warning = load_dataframe(uploaded_file)
            st.session_state.df = df
            st.success(f"{df.shape[0]}행 × {df.shape[1]}열 로드됨")
            if warning:
                st.warning(warning)
            with st.expander("데이터 미리보기"):
                st.dataframe(df.head(10), use_container_width=True)
        except Exception as e:
            st.error(f"파일 로드 실패: {e}")
            st.session_state.df = None
    elif "df" not in st.session_state:
        st.session_state.df = None

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_dataframe(uploaded_file) -> tuple[pd.DataFrame, str | None]:
    """Load CSV or Excel with encoding/separator auto-detection.

    Returns (df, warning) where warning is non-None if bad lines were skipped.
    """
    if not uploaded_file.name.endswith(".csv"):
        return pd.read_excel(uploaded_file), None

    raw = uploaded_file.read()
    for encoding in ("utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue

        buf = io.StringIO(text)
        try:
            return pd.read_csv(buf, sep=None, engine="python"), None
        except Exception:
            pass

        buf.seek(0)
        try:
            df = pd.read_csv(buf, sep=None, engine="python", on_bad_lines="skip")
            return df, "일부 형식이 맞지 않는 행이 건너뛰어졌습니다."
        except Exception:
            continue

    raise ValueError("지원하지 않는 파일 형식 또는 인코딩입니다.")


def build_system_message(df: pd.DataFrame | None) -> str:
    base = "당신은 친절하고 유능한 AI 어시스턴트입니다."
    if df is None:
        return base
    # Cap rows/cols shown to keep token usage reasonable
    describe_str = df.describe(include="all").to_string()
    head_str = df.head(5).to_string()
    return (
        base
        + f"""

사용자가 데이터 파일을 업로드했습니다. 아래 정보를 바탕으로 질문에 답하세요.

[데이터 크기]
{df.shape[0]}행 × {df.shape[1]}열

[컬럼 및 타입]
{df.dtypes.to_string()}

[기초 통계]
{describe_str}

[처음 5행]
{head_str}
"""
    )


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
        system_msg = {"role": "system", "content": build_system_message(st.session_state.df)}
        chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        stream = client.chat.completions.create(
            model=model,
            messages=[system_msg] + chat_history,
            temperature=temperature,
            stream=True,
        )
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
    except Exception as e:
        st.error(f"응답 생성 실패: {e}")
