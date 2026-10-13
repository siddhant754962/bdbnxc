
import re
from urllib.parse import parse_qs, urlparse

import re
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import build_rag_chain, ask_question


load_dotenv()


def _youtube_video_id(source: str) -> str | None:
    """Extract a video ID from common YouTube URL formats."""
    try:
        parsed = urlparse(source.strip())
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/").split("/")[0] or None

    if host in {
        "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
        "youtube-nocookie.com", "www.youtube-nocookie.com",
    }:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if not video_id:
            match = re.match(r"^/(?:shorts|embed|live)/([^/?]+)", parsed.path)
            video_id = match.group(1) if match else ""
        return video_id or None

    return None


def _try_public_youtube_transcript(source: str, language: str) -> str:
    """Try captions that are already publicly accessible; never downloads audio."""
    video_id = _youtube_video_id(source)
    if not video_id:
        return ""

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        preferred_languages = ["en", "hi"] if language.lower() == "english" else ["hi", "en"]
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=preferred_languages)
        snippets = getattr(fetched, "snippets", None)
        if snippets is None:
            snippets = fetched.to_raw_data()

        text_parts = []
        for snippet in snippets:
            value = snippet.get("text", "") if isinstance(snippet, dict) else getattr(snippet, "text", "")
            if value and value.strip():
                text_parts.append(value.strip())
        return " ".join(text_parts).strip()
    except Exception as exc:
        # A cloud host may be blocked by YouTube for captions too; fall through
        # to the audio route and let the UI offer direct file upload if blocked.
        print(f"Public YouTube captions unavailable; trying audio instead: {type(exc).__name__}: {exc}")
        return ""


# ----------------------------------
# MAIN AI VIDEO PIPELINE
# ----------------------------------

def run_pipeline(source: str, language: str = "english") -> dict:
    print("Starting AI Video Assistant...")

    # 1. For YouTube URLs, first try captions that are already available.
    # This can avoid audio downloading when captions are accessible.
    transcript = _try_public_youtube_transcript(source, language)
    if transcript:
        print("Loaded public YouTube captions; skipping audio download.")
    else:
        # 2. Fall back to audio processing. If YouTube blocks cloud downloads,
        # the Streamlit UI offers direct media upload as the reliable alternative.
        chunks = process_input(source)
        transcript = transcribe_all(chunks, language)

    if not transcript or not transcript.strip():
        raise ValueError("Transcription is empty. Cannot continue.")

    print(
        f"Raw transcription (first 300 characters): "
        f"{transcript[:300]}"
    )

    # 3. Generate video title
    title = generate_title(transcript)

    # 4. Generate summary
    summary = summarize(transcript)

    # 5. Extract useful information
    action_items = extract_action_items(transcript)

    decisions = extract_key_decisions(transcript)

    open_questions = extract_questions(transcript)

    # 6. Build RAG chain using the transcript
    rag_chain = build_rag_chain(transcript, source)

    # 7. Return all results
    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": open_questions,
        "rag_chain": rag_chain,
    }


# ----------------------------------
# CLI ENTRY POINT
# ----------------------------------

if __name__ == "__main__":

    source = input(
        "Enter YouTube URL or local file path: "
    ).strip()

    language = (
        input("Language (english/hinglish): ").strip()
        or "english"
    )

    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"📌 Title: {result['title']}")
    print(f"\n📋 Summary:\n{result['summary']}")
    print(f"\n✅ Action Items:\n{result['action_items']}")
    print(f"\n🔑 Key Decisions:\n{result['key_decisions']}")
    print(f"\n❓ Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    # ----------------------------------
    # PHASE 2 — CHAT WITH VIDEO
    # ----------------------------------

    print("\n💬 Chat with your video (type 'exit' to quit)\n")

    rag_chain = result["rag_chain"]

    while True:
        question = input("You: ").strip()

        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break

        if not question:
            continue

        try:
            answer = ask_question(rag_chain, question)
            print(f"\n🤖 Assistant: {answer}\n")

        except Exception as error:
            print(f"\n❌ Error answering question: {error}\n")
