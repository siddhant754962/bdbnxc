"""Audio input processing for SiddAi VideoDost.

This module deliberately does not read or require YouTube cookies.
YouTube URL downloads can still be refused by YouTube on cloud-hosted IPs;
when that happens, the error points the user to the supported media-file path.
"""

from pathlib import Path
import shutil

import yt_dlp
from yt_dlp.utils import DownloadError
from pydub import AudioSegment

# Render may not have a system FFmpeg binary. imageio-ffmpeg ships a compatible
# binary for common platforms; use it for MP3/M4A/MP4 and other media decoding.
try:
    import imageio_ffmpeg

    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    # Local/system FFmpeg will continue to work if this optional package is absent.
    pass

# Render may not have a system FFmpeg binary. imageio-ffmpeg ships a compatible
# binary for common platforms; use it for MP3/M4A/MP4 and other media decoding.
try:
    import imageio_ffmpeg

    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    # Local/system FFmpeg will continue to work if this optional package is absent.
    pass


BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _is_url(source: str) -> bool:
    return source.startswith(("https://", "http://"))


def download_youtube_audio(url: str) -> str:
    """Try to download audio without cookies; report cloud bot blocks clearly."""
    output_path = str(DOWNLOAD_DIR / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "retries": 1,
        "fragment_retries": 1,
        "socket_timeout": 30,
    }

    # Use Deno for YouTube's JavaScript challenges only if already installed.
    # This may help extraction, but does not bypass sign-in or IP restrictions.
    deno_path = shutil.which("deno")
    if deno_path:
        ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as exc:
        detail = str(exc)
        lowered = detail.lower()
        if (
            "sign in to confirm" in lowered
            or "you're not a bot" in lowered
            or "you are not a bot" in lowered
            or "confirm you're not a bot" in lowered
        ):
            raise RuntimeError(
                "YouTube blocked the audio request from this server with its "
                "sign-in/bot-verification check. This processor does not use "
                "cookies, and no code-only change can guarantee that YouTube "
                "will allow downloads from a cloud-hosting IP. Use a permitted "
                "audio/video file instead. On a deployed web app, the file-upload "
                "control must be provided by app.py; this module alone cannot "
                "read files from your personal computer."
            ) from exc
        raise RuntimeError(f"yt-dlp could not download this URL: {detail}") from exc

    if not info:
        raise RuntimeError("yt-dlp returned no video information for this URL.")

    video_id = info.get("id")
    if not video_id:
        raise RuntimeError("yt-dlp did not return a video ID for this URL.")

    # Pick the downloaded media file itself, not partial files or generated WAVs.
    downloaded_files = [
        path
        for path in DOWNLOAD_DIR.glob(f"{video_id}.*")
        if path.is_file()
        and path.stem == video_id
        and path.suffix.lower() not in {".part", ".ytdl", ".wav"}
        and not path.stem.endswith("_clean")
    ]

    if not downloaded_files:
        raise FileNotFoundError(
            f"yt-dlp finished but the downloaded media file was not found for {video_id}."
        )

    return str(max(downloaded_files, key=lambda path: path.stat().st_mtime))


def convert_to_wav(input_path: str) -> str:
    """Convert audio/video media into mono, 16 kHz WAV for transcription."""
    input_file = Path(input_path)
    if not input_file.is_file():
        raise FileNotFoundError(f"Media file not found: {input_file}")

    output_path = input_file.with_name(input_file.stem + "_clean.wav")

    try:
        audio = AudioSegment.from_file(str(input_file))
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(str(output_path), format="wav")
    except Exception as exc:
        raise RuntimeError(
            "Could not decode this media file. Make sure FFmpeg is installed "
            "in the runtime and the file format is supported."
        ) from exc

    return str(output_path)


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list[str]:
    """Split a WAV into chunks for the transcription service."""
    if chunk_minutes <= 0:
        raise ValueError("chunk_minutes must be greater than zero")

    wav_file = Path(wav_path)
    if not wav_file.is_file():
        raise FileNotFoundError(f"WAV file not found: {wav_file}")

    audio = AudioSegment.from_wav(str(wav_file))
    chunk_ms = chunk_minutes * 60 * 1000
    chunks: list[str] = []

    for index, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = wav_file.with_name(f"{wav_file.stem}_chunk_{index}.wav")
        chunk.export(str(chunk_path), format="wav")
        chunks.append(str(chunk_path))

    if not chunks:
        raise ValueError("The audio file is empty; no audio chunks were created.")

    return chunks


def process_input(source: str) -> list[str]:
    """Accept a URL or a media-file path and return WAV chunks.

    For a deployed Streamlit app, the user's browser file must first be uploaded
    by app.py; a path on the user's own computer is not visible to Render.
    """
    source = source.strip()
    if not source:
        raise ValueError("Please provide a URL or local audio/video file path.")

    if _is_url(source):
        media_path = download_youtube_audio(source)
    else:
        media_path = str(Path(source).expanduser().resolve())
        if not Path(media_path).is_file():
            raise FileNotFoundError(
                f"Media file not found: {media_path}. On Render, use a file-upload "
                "control in the web app; paths from your personal computer are not accessible."
            )

    clean_wav_path = convert_to_wav(media_path)
    return chunk_audio(clean_wav_path)
