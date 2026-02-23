"""YouTube transcript extraction service."""

import os
import re
import tempfile
import traceback
from typing import Optional
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.utils.chunking import clean_text
from app.utils.logging_config import get_logger

logger = get_logger("youtube")


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL. Supports youtube.com/watch?v=, youtu.be/, embed, /v/. Strips fragment and extra params."""
    s = (url or "").strip()
    if not s:
        return None
    # Strip fragment (#...)
    if "#" in s:
        s = s.split("#", 1)[0]
    parsed = urlparse(s)
    if not parsed.hostname:
        return None
    host = parsed.hostname.lower().replace("www.", "")
    if host == "youtube.com":
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            return vid if isinstance(vid, str) and vid else None
        if parsed.path.startswith("/embed/"):
            parts = parsed.path.split("/")
            return parts[2] if len(parts) > 2 else None
        if parsed.path.startswith("/v/"):
            parts = parsed.path.split("/")
            return parts[2] if len(parts) > 2 else None
    if host == "youtu.be":
        # path is /VIDEO_ID (maybe with query)
        path = (parsed.path or "").strip("/")
        return path.split("?")[0] or None
    return None


def _user_friendly_transcript_error(err: Exception) -> str:
    """Convert library/parsing errors into a clear message for the user."""
    msg = str(err).lower()
    if "no element found" in msg or "line 1, column 0" in msg:
        return (
            "Could not load captions for this video. YouTube may have changed their page, "
            "or this video might not have transcripts available. Try a different video "
            "that you know has captions (CC) enabled."
        )
    if "json" in msg or "parse" in msg or "xml" in msg:
        return (
            "Caption data for this video couldn't be read. Try another video with "
            "English (or other) captions enabled."
        )
    return str(err)


def _fetch_transcript_ytdlp(full_url: str, video_id: str) -> Optional[str]:
    """Fallback: fetch subtitles using yt-dlp. Returns transcript text or None."""
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp not installed, skipping yt-dlp transcript fallback")
        return None

    out_dir = tempfile.mkdtemp(prefix="saiv_yt_")
    out_tmpl = os.path.join(out_dir, "sub")
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt/srt/best",
        "outtmpl": out_tmpl,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([full_url])
            for name in os.listdir(out_dir):
                if name.endswith((".vtt", ".srt")):
                    path = os.path.join(out_dir, name)
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    lines = []
                    for line in content.splitlines():
                        line = line.strip()
                        if not line or line.isdigit():
                            continue
                        if "-->" in line:
                            continue
                        if line.startswith("WEBVTT") or line.startswith("Kind:"):
                            continue
                        lines.append(line)
                    text = " ".join(lines)
                    text = re.sub(r"<[^>]+>", "", text)
                    text = clean_text(text)
                    if len(text) >= 50:
                        return text
                    break
    except Exception as e:
        traceback.print_exc()
        logger.warning("yt-dlp transcript fallback failed", video_id=video_id, error=str(e))
    finally:
        try:
            for name in os.listdir(out_dir):
                os.remove(os.path.join(out_dir, name))
            os.rmdir(out_dir)
        except OSError:
            pass

    return None


def fetch_transcript(url: str) -> tuple[str, str]:
    """
    Fetch transcript for a YouTube video.
    Returns (title, transcript_text).
    Raises ValueError on failure with a clear message.
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL: could not extract video ID")

    full_url = url if url.startswith("http") else f"https://www.youtube.com/watch?v={video_id}"

    transcript_list = None
    api_failed_with_exception = None

    # 1) get_transcript with explicit language preference
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
    except TranscriptsDisabled:
        traceback.print_exc()
        raise ValueError(
            "Transcripts are disabled for this video. Try another video with captions (CC) enabled."
        )
    except VideoUnavailable:
        traceback.print_exc()
        raise ValueError("Video is unavailable or private.")
    except NoTranscriptFound:
        transcript_list = None
        api_failed_with_exception = None
    except Exception as e:
        api_failed_with_exception = e
        traceback.print_exc()
        logger.warning("get_transcript failed", video_id=video_id, error=str(e))
        transcript_list = None

    # 2) list_transcripts and pick first available (prefer manually created)
    if not transcript_list:
        list_obj = None
        try:
            list_obj = YouTubeTranscriptApi.list_transcripts(video_id)
            # Prefer manually created, then auto-generated
            try:
                transcript = list_obj.find_manually_created_transcript(["en", "en-US", "en-GB"])
            except Exception:
                transcript = list_obj.find_generated_transcript(["en", "en-US", "en-GB"])
            transcript_list = transcript.fetch()
        except TranscriptsDisabled:
            traceback.print_exc()
            raise ValueError(
                "Transcripts are disabled for this video. Try another with captions (CC) enabled."
            )
        except VideoUnavailable:
            traceback.print_exc()
            raise ValueError("Video is unavailable or private.")
        except NoTranscriptFound:
            pass
        except Exception as list_err:
            api_failed_with_exception = list_err
            traceback.print_exc()
            if list_obj:
                try:
                    for t in list_obj:
                        transcript_list = t.fetch()
                        break
                except Exception:
                    traceback.print_exc()
                    pass

    # 3) yt-dlp fallback
    if not transcript_list:
        yt_dlp_text = _fetch_transcript_ytdlp(full_url, video_id)
        if yt_dlp_text:
            return f"YouTube Video {video_id}", yt_dlp_text
        if api_failed_with_exception is not None:
            raise ValueError(_user_friendly_transcript_error(api_failed_with_exception))
        raise ValueError(
            "No transcript found for this video. Make sure the video has captions (CC) enabled."
        )

    try:
        segments = [item["text"] for item in transcript_list]
    except (KeyError, TypeError) as e:
        traceback.print_exc()
        logger.exception("Unexpected transcript format", video_id=video_id)
        raise ValueError(_user_friendly_transcript_error(e))

    raw_text = " ".join(segments)
    raw_text = re.sub(r"\[.*?\]", "", raw_text)
    text = clean_text(raw_text)

    if not text or len(text) < 50:
        yt_dlp_text = _fetch_transcript_ytdlp(full_url, video_id)
        if yt_dlp_text:
            return f"YouTube Video {video_id}", yt_dlp_text
        raise ValueError(
            "Transcript is empty or too short. The video may have minimal captions."
        )

    return f"YouTube Video {video_id}", text
