from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import yaml
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


CONFIG_PATH = Path("config/settings.yaml")


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_transcript(video_id: str, language: str, include_auto_generated: bool) -> List[dict]:
    languages = [language]
    if include_auto_generated:
        languages.append(f"{language}-orig")

    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        # Convert FetchedTranscript to list of dicts with text, start, duration
        segments = [
            {
                "text": entry.text,
                "start": entry.start,
                "duration": entry.duration,
            }
            for entry in transcript
        ]
        return segments
    except (TranscriptsDisabled, NoTranscriptFound):
        return []


def save_transcript(video_id: str, transcript: List[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"video_id": video_id, "transcript": transcript}
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def download_video_transcript(video_id: str, output_path: Path | None = None) -> Path:
    settings = load_settings()
    yt_cfg = settings.get("youtube", {})

    language = yt_cfg.get("language", "en")
    include_auto = bool(yt_cfg.get("include_auto_generated", True))

    transcript = fetch_transcript(video_id, language=language, include_auto_generated=include_auto)

    if output_path is None:
        raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
        output_path = Path(raw_dir) / f"youtube_transcript_{video_id}.json"

    save_transcript(video_id, transcript, output_path)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a YouTube transcript for a given video ID and save as JSON."
    )
    parser.add_argument(
        "video_id",
        help="YouTube video ID (the part after v= in the URL).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output JSON path (default: data/raw/youtube_transcript_<id>.json)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    output = Path(args.output) if args.output is not None else None
    output_path = download_video_transcript(args.video_id, output)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()

