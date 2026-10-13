"""SiddAi VideoDost— cinematic Streamlit frontend.

Run from the project directory:
    uv run streamlit run streamlit_app.py

Uses the existing backend:
    main.run_pipeline
    core.rag_engine.ask_question

Note: the animated waiting panel is an activity indicator. Exact stage-by-stage
progress requires the backend to expose progress callbacks.
"""

import html
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from main import run_pipeline
from core.rag_engine import ask_question

load_dotenv()

st.set_page_config(
    page_title="SiddAi VideoDost",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# DESIGN SYSTEM
# ---------------------------------------------------------------------

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=DM+Sans:wght@400;500;600&display=swap');

:root {
  --bg: #07090d;
  --panel: #10151d;
  --panel-2: #0d131a;
  --ink: #edf3f8;
  --muted: #9aa7b5;
  --line: #27313d;
  --mint: #7cffb2;
  --mint-2: #54e995;
  --cyan: #68dfff;
}
html { color-scheme: dark; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: var(--bg); color: var(--ink);
}
.stApp {
  background: radial-gradient(ellipse at 50% -20%, #15232b 0%, var(--bg) 56%);
  color: var(--ink);
  font-family: 'DM Sans', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
  display: none !important;
}
.block-container { padding-top: 1.7rem; padding-bottom: 4rem; max-width: 1120px; }
h1, h2, h3, h4 {
  color: var(--ink);
  font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
  letter-spacing: -0.025em;
}
p, label, [data-testid="stMarkdownContainer"] { color: var(--ink); }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #090e13;
  border-right: 1px solid #1e2b31;
}
[data-testid="stSidebar"] * { color: #e8f0ec; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
  background: #101720; border: 1px solid #2b4547;
  color: #fff; border-radius: 10px;
}
[data-testid="stSidebar"] input::placeholder { color: #829c9a; }
[data-testid="stSidebar"] label p { color: #b8c9c8 !important; font-size: .88rem; }
.brand { display:flex; align-items:center; gap:.7rem; margin: .3rem 0 1.8rem; }
.brand-mark {
  width:38px; height:38px; border-radius:12px;
  background:var(--mint); color:#07130d;
  display:grid; place-items:center; font-size:1.25rem;
  box-shadow:0 0 24px rgba(124,255,178,.14);
}
.brand-name { font-family:'Bricolage Grotesque',sans-serif; font-weight:700; font-size:1.3rem; color:#fff; }
.side-note { font-size:.82rem; color:#91a8a7 !important; line-height:1.55; margin-top:1.1rem; }
[data-testid="stSidebar"] button[kind="primary"] {
  background:var(--mint); color:#07130d !important; border:none;
  font-weight:700; border-radius:10px; padding:.65rem 1rem;
}
[data-testid="stSidebar"] button[kind="primary"] p { color:#07130d !important; }
[data-testid="stSidebar"] button[kind="primary"]:hover { background:var(--mint-2); }
[data-testid="stSidebar"] button[kind="secondary"] {
  background:transparent; border:1px solid #304349; border-radius:10px;
}
.stButton > button:focus-visible, input:focus-visible {
  outline:3px solid var(--mint) !important; outline-offset:2px;
}

/* Hero */
.hero {
  position:relative; overflow:hidden;
  background:linear-gradient(135deg, #111b23 0%, #0b1016 62%, #10231d 100%);
  border:1px solid #263740; border-radius:22px;
  padding:3rem 3rem 2.7rem; margin-bottom:1.4rem;
  box-shadow:0 18px 60px rgba(0,0,0,.25);
}
.hero:after {
  content:''; position:absolute; width:240px; height:240px; right:-65px; top:-100px;
  border-radius:50%; border:1px solid rgba(124,255,178,.2);
  box-shadow:0 0 0 22px rgba(124,255,178,.025), 0 0 0 48px rgba(104,223,255,.025);
  pointer-events:none;
}
.eyebrow {
  color:var(--mint); text-transform:uppercase; letter-spacing:.16em;
  font-size:.75rem; font-weight:700; margin-bottom:.9rem;
}
.hero h1 { color:#fff; font-size:clamp(2.1rem,4.5vw,3.35rem); line-height:1.05; margin:0 0 1rem; max-width:17ch; }
.hero p { color:#bfd0d0; font-size:1.04rem; max-width:58ch; line-height:1.7; margin:0; }
.step {
  background:linear-gradient(145deg, #121922, #0d1117);
  border:1px solid var(--line); border-radius:15px;
  padding:1.2rem 1.25rem; min-height:132px;
  transition:transform .2s ease, border-color .2s ease;
}
.step:hover { transform:translateY(-3px); border-color:#4d8f7a; }
.step b { font-family:'Bricolage Grotesque',sans-serif; font-size:1.05rem; display:block; margin-bottom:.45rem; }
.step span { color:var(--muted); font-size:.92rem; line-height:1.55; }

/* Results */
.result-title { font-size:clamp(1.6rem,3vw,2.25rem); margin:.2rem 0 .35rem; line-height:1.15; }
.meta { color:var(--muted); font-size:.9rem; margin-bottom:1.1rem; }
.stat-row { display:flex; gap:.55rem; flex-wrap:wrap; margin:.5rem 0 1.35rem; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:999px; padding:.38rem .85rem; font-size:.86rem; color:var(--muted); }
.stat b { color:var(--ink); font-weight:600; margin-right:.25rem; }
.stTabs [data-baseweb="tab-list"] { gap:1.35rem; border-bottom:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { padding:.7rem 0; font-weight:600; color:var(--muted); }
.stTabs [aria-selected="true"] { color:var(--ink); }
.stTabs [data-baseweb="tab-highlight"] { background:var(--mint); height:3px; border-radius:2px; }
.section-label { font-family:'Bricolage Grotesque',sans-serif; font-weight:700; font-size:1.05rem; margin-bottom:.55rem; }
.summary-text { font-size:1.03rem; line-height:1.8; max-width:78ch; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--panel); border-color:var(--line) !important; border-radius:14px;
}
[data-testid="stChatMessage"] {
  background:var(--panel); border:1px solid var(--line);
  border-radius:14px; padding:1rem 1.15rem; margin-bottom:.65rem;
}
[data-testid="stChatInput"] { border-radius:14px; border:1px solid #303c49; background:#0e141b; }
[data-testid="stChatInput"] textarea { color:var(--ink); -webkit-text-fill-color:var(--ink); }
[data-testid="stTextArea"] textarea { background:#0e141b; color:var(--ink); -webkit-text-fill-color:var(--ink); border-color:#303c49; border-radius:12px; }
.chat-empty { color:var(--muted); font-size:.94rem; margin:.2rem 0 .8rem; }
[data-testid="stMain"] .stButton > button, [data-testid="stDownloadButton"] button {
  border-radius:999px; border:1px solid #303c49; background:#111821; color:var(--ink);
  font-size:.9rem; padding:.45rem 1rem; transition:all .18s ease;
}
[data-testid="stMain"] .stButton > button:hover, [data-testid="stDownloadButton"] button:hover {
  border-color:var(--mint); color:var(--mint); transform:translateY(-1px);
}

/* Waiting / activity panel */
.processing-panel {
  margin:.4rem 0 1rem; padding:1.35rem;
  border:1px solid #263c3b; border-radius:18px;
  background:radial-gradient(circle at 8% 0%, #132a27 0%, #0d131a 48%, #0a0e13 100%);
  overflow:hidden;
}
.processing-top { display:flex; align-items:center; gap:1rem; }
.processing-orb {
  position:relative; flex:0 0 58px; width:58px; height:58px; border-radius:50%;
  border:1px solid #2e6657;
  background:radial-gradient(circle, #7cffb2 0%, #1d7557 20%, #10231f 62%, transparent 70%);
  box-shadow:0 0 24px rgba(124,255,178,.22);
  animation:orb-pulse 2s ease-in-out infinite;
}
.processing-orb:before, .processing-orb:after {
  content:''; position:absolute; inset:-7px; border:1px solid rgba(124,255,178,.45);
  border-radius:50%; animation:orbit 3s linear infinite;
}
.processing-orb:after { inset:5px -11px; border-color:rgba(104,223,255,.55); animation-duration:4s; animation-direction:reverse; }
.processing-title { color:#f0f7f4; font-size:1.1rem; font-weight:700; margin:0 0 .25rem; }
.processing-subtitle { color:#a6b8b8; font-size:.9rem; margin:0; line-height:1.5; }
.processing-track { height:5px; background:#1c2a30; border-radius:999px; margin-top:1.25rem; overflow:hidden; }
.processing-track span {
  display:block; width:36%; height:100%; border-radius:999px;
  background:linear-gradient(90deg, #54e995, #68dfff);
  box-shadow:0 0 16px rgba(104,223,255,.45);
  animation:loading-sweep 1.5s ease-in-out infinite;
}
.activity-line { color:#d7e9e4; font-size:.92rem; margin-top:.85rem; }
.processing-chips { display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.85rem; }
.processing-chip { border:1px solid #263c3b; background:#101b20; color:#b9d9d0; border-radius:999px; padding:.32rem .65rem; font-size:.77rem; }
.small-muted { color:var(--muted); font-size:.8rem; }
@keyframes orb-pulse { 0%,100% { transform:scale(.96); filter:brightness(.9); } 50% { transform:scale(1.05); filter:brightness(1.25); } }
@keyframes orbit { from { transform:rotate(0deg) scaleX(.72); } to { transform:rotate(360deg) scaleX(.72); } }
@keyframes loading-sweep { 0% { transform:translateX(-110%); } 100% { transform:translateX(310%); } }
@media (max-width:700px) { .hero { padding:2rem 1.35rem; border-radius:16px; } .processing-top { align-items:flex-start; } }
@media (prefers-reduced-motion:reduce) { * { transition:none !important; animation:none !important; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------

DEFAULTS = {
    "video_result": None,
    "chat_history": [],
    "processing_error": None,
    "source_label": "",
    "processed_at": None,
    "pending_question": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_video():
    st.session_state.video_result = None
    st.session_state.chat_history = []
    st.session_state.processing_error = None
    st.session_state.source_label = ""
    st.session_state.processed_at = None
    st.session_state.pending_question = None


def queue_question(question: str):
    st.session_state.pending_question = question


def build_notes_markdown(result: dict) -> str:
    return (
        f"# {result.get('title', 'SiddAi VideoDost')}\n\n"
        f"## Summary\n{result.get('summary', '')}\n\n"
        f"## Action items\n{result.get('action_items', '')}\n\n"
        f"## Key decisions\n{result.get('key_decisions', '')}\n\n"
        f"## Open questions\n{result.get('open_questions', '')}\n"
    )


def build_chat_markdown(history: list) -> str:
    lines = ["# Chat with video", ""]
    for message in history:
        who = "You" if message["role"] == "user" else "SiddAi VideoDost"
        lines.append(f"**{who}:** {message['content']}\n")
    return "\n".join(lines)


def run_pipeline_in_background(source: str, language: str, outcome: dict):
    """Run backend work off the UI thread; only write to this shared result dict."""
    try:
        outcome["result"] = run_pipeline(source=source, language=language)
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        outcome["done"] = True


def render_processing_panel(activity: str, elapsed_seconds: int):
    safe_activity = html.escape(activity)
    elapsed = f"{elapsed_seconds // 60:02d}:{elapsed_seconds % 60:02d}"
    st.markdown(
        f"""
        <div class="processing-panel">
          <div class="processing-top">
            <div class="processing-orb"></div>
            <div>
              <p class="processing-title">SiddAi VideoDost is building your knowledge base</p>
              <p class="processing-subtitle">Hang tight. Longer videos and first-time embedding setup can take a little while.</p>
            </div>
          </div>
          <div class="processing-track"><span></span></div>
          <div class="activity-line">✦ &nbsp;{safe_activity}</div>
          <div class="processing-chips">
            <span class="processing-chip">01 · Prepare audio</span>
            <span class="processing-chip">02 · Transcribe</span>
            <span class="processing-chip">03 · Create notes</span>
            <span class="processing-chip">04 · Index for chat</span>
          </div>
          <p class="small-muted">Elapsed time: {elapsed} · The bar is an activity animation, not an exact percentage.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">🎥</div>'
        '<div class="brand-name">SiddAi VideoDost</div></div>',
        unsafe_allow_html=True,
    )

    source = st.text_input(
        "YouTube video link (optional if uploading a file)",
        placeholder="https://youtube.com/watch?v=...",
    )
    uploaded_file = st.file_uploader(
        "Or upload audio/video (avoids YouTube download blocks)",
        type=["mp3", "wav", "m4a", "mp4", "webm", "mov", "mkv", "avi", "mpeg", "mpga", "aac", "ogg", "flac"],
        accept_multiple_files=False,
        help="Upload a media file from your computer. The app processes the uploaded file directly and does not need YouTube cookies.",
    )
    language = st.selectbox(
        "Spoken language",
        options=["english", "hinglish"],
        format_func=lambda value: value.capitalize(),
    )
    process_clicked = st.button(
        "✦  Process video",
        type="primary",
        use_container_width=True,
    )

    if st.session_state.video_result is not None:
        if st.button("Start over", use_container_width=True):
            reset_video()
            st.rerun()

    st.markdown(
        '<p class="side-note">SiddAi VideoDost turns video speech into useful notes. '
        'Paste a YouTube link or upload a media file directly. Direct upload avoids YouTube download authentication blocks. '
        'Keep this tab open while processing is underway.</p>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# PROCESS VIDEO
# ---------------------------------------------------------------------

if process_clicked:
    selected_source = source.strip()
    source_display_name = selected_source

    # Uploaded files are saved inside the running app so the existing
    # process_input -> transcription -> notes -> RAG pipeline can consume them.
    # If both fields are filled, the uploaded file takes priority.
    if uploaded_file is not None:
        allowed_extensions = {
            ".mp3", ".wav", ".m4a", ".mp4", ".webm", ".mov", ".mkv", ".avi",
            ".mpeg", ".mpga", ".aac", ".ogg", ".flac",
        }
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in allowed_extensions:
            st.warning("Unsupported media format. Upload MP3, WAV, M4A, MP4, WebM, MOV, MKV, AVI, AAC, OGG, or FLAC.")
            selected_source = ""
        else:
            upload_dir = Path(__file__).resolve().parent / "downloads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_path = upload_dir / f"upload_{uuid.uuid4().hex}{suffix}"
            upload_path.write_bytes(uploaded_file.getvalue())
            selected_source = str(upload_path)
            source_display_name = uploaded_file.name

    if not selected_source:
        st.warning("Paste a YouTube link or upload an audio/video file to continue.")
    else:
        reset_video()
        outcome = {"done": False, "result": None, "error": None}
        worker = threading.Thread(
            target=run_pipeline_in_background,
            args=(selected_source, language, outcome),
            daemon=True,
        )

        activity_messages = [
            "Preparing the video input and checking the audio source…",
            "Extracting speech and turning audio into transcript text…",
            "Reading the transcript and generating your study notes…",
            "Organizing transcript chunks so chat can retrieve relevant context…",
            "Finishing up and preparing your SiddAi VideoDost workspace…",
        ]
        start_time = time.monotonic()
        worker.start()

        waiting_area = st.empty()
        while not outcome["done"]:
            elapsed = int(time.monotonic() - start_time)
            # Rotating messages keep the interface alive, but they are
            # illustrative until the backend provides real progress events.
            phase = min(elapsed // 7, len(activity_messages) - 1)
            with waiting_area.container():
                render_processing_panel(activity_messages[phase], elapsed)
            time.sleep(0.7)

        if outcome["error"]:
            st.session_state.processing_error = outcome["error"]
        elif outcome["result"] is not None:
            st.session_state.video_result = outcome["result"]
            st.session_state.source_label = source.strip()
            st.session_state.processed_at = datetime.now()
            st.toast("Your notes are ready", icon="✅")
            st.rerun()
        else:
            st.session_state.processing_error = (
                "The pipeline finished without returning a result."
            )

# ---------------------------------------------------------------------
# ERROR STATE
# ---------------------------------------------------------------------

if st.session_state.processing_error:
    error_text = st.session_state.processing_error
    st.error(
        "SiddAi VideoDost couldn't process this input. Check the URL or media file, "
        "then try again."
    )
    if "youtube blocked" in error_text.lower() or "sign in to confirm" in error_text.lower() or "not a bot" in error_text.lower():
        st.info(
            "YouTube has blocked automatic audio download from this server. "
            "Use the audio/video upload control in the sidebar to continue without cookies."
        )
    with st.expander("Technical details"):
        st.code(error_text)

# ---------------------------------------------------------------------
# MAIN VIEW
# ---------------------------------------------------------------------

result = st.session_state.video_result

if result is None:
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">Your personal video study space</div>
          <h1>Turn any lecture into notes you can question.</h1>
          <p>Drop in a YouTube link or a local media file. SiddAi VideoDost creates a
          transcript, summarizes the key ideas, extracts action items, and lets
          you chat with the video content.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        '<div class="step"><b>01 · Add a video</b>'
        '<span>Paste a YouTube link or upload an audio/video file in the sidebar.</span></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        '<div class="step"><b>02 · Get the notes</b>'
        '<span>Review the summary, action items, decisions, and questions.</span></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        '<div class="step"><b>03 · Ask and learn</b>'
        '<span>Ask follow-up questions grounded in the transcript.</span></div>',
        unsafe_allow_html=True,
    )
else:
    transcript = result.get("transcript") or ""
    word_count = len(transcript.split())
    talk_minutes = max(1, round(word_count / 150))
    read_minutes = max(1, round(word_count / 220))
    processed_at = st.session_state.processed_at
    stamp = processed_at.strftime("%d %b %Y, %H:%M") if processed_at else ""
    safe_title = html.escape(str(result.get("title", "Untitled video")))

    st.markdown(
        f'<h1 class="result-title">{safe_title}</h1>'
        f'<div class="meta">Processed {html.escape(stamp)}</div>'
        '<div class="stat-row">'
        f'<span class="stat"><b>~{talk_minutes} min</b> speech</span>'
        f'<span class="stat"><b>{word_count:,}</b> words</span>'
        f'<span class="stat"><b>~{read_minutes} min</b> read</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    notes_tab, transcript_tab = st.tabs(["✦ Notes", "▤ Transcript"])

    with notes_tab:
        st.markdown(
            '<div class="section-label">Summary</div>',
            unsafe_allow_html=True,
        )
        safe_summary = html.escape(str(result.get("summary", ""))).replace("\n", "<br>")
        st.markdown(
            f'<div class="summary-text">{safe_summary}</div>',
            unsafe_allow_html=True,
        )
        st.write("")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            with st.container(border=True):
                st.markdown('<div class="section-label">Action items</div>', unsafe_allow_html=True)
                st.markdown(str(result.get("action_items", "No action items found.")))
        with col_b:
            with st.container(border=True):
                st.markdown('<div class="section-label">Key decisions</div>', unsafe_allow_html=True)
                st.markdown(str(result.get("key_decisions", "No key decisions found.")))
        with col_c:
            with st.container(border=True):
                st.markdown('<div class="section-label">Open questions</div>', unsafe_allow_html=True)
                st.markdown(str(result.get("open_questions", "No open questions found.")))

        st.write("")
        st.download_button(
            "Download notes (.md)",
            data=build_notes_markdown(result),
            file_name="siddai-videodost-notes.md",
            mime="text/markdown",
        )

    with transcript_tab:
        st.text_area(
            "Full transcript",
            value=transcript,
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )
        st.download_button(
            "Download transcript (.txt)",
            data=transcript,
            file_name="siddai-videodost-transcript.txt",
            mime="text/plain",
        )

    st.divider()
    st.markdown("## Ask about this video")

    if not st.session_state.chat_history:
        st.markdown(
            '<p class="chat-empty">Need a starting point? Try a suggested question.</p>',
            unsafe_allow_html=True,
        )
        suggestions = [
            "What are the main points?",
            "Explain the key concepts simply",
            "Give me 5 revision questions",
        ]
        suggestion_cols = st.columns(len(suggestions))
        for col, suggested_question in zip(suggestion_cols, suggestions):
            col.button(
                suggested_question,
                key=f"suggestion_{suggested_question}",
                on_click=queue_question,
                args=(suggested_question,),
                use_container_width=True,
            )

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    typed_question = st.chat_input("Ask a question about this video…")
    question = typed_question or st.session_state.pending_question
    st.session_state.pending_question = None

    if question and question.strip():
        question = question.strip()
        st.session_state.chat_history.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.markdown(question)

        try:
            with st.chat_message("assistant"):
                with st.spinner("Searching the transcript…"):
                    answer = ask_question(result["rag_chain"], question)
                st.markdown(answer)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )
        except Exception as error:
            error_message = f"I couldn't answer that: {error}"
            with st.chat_message("assistant"):
                st.error(error_message)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": error_message}
            )

    if st.session_state.chat_history:
        st.download_button(
            "Download chat (.md)",
            data=build_chat_markdown(st.session_state.chat_history),
            file_name="siddai-videodost-chat.md",
            mime="text/markdown",
        )
