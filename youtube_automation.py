import os
import json
import random
import time
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import requests
import schedule
from dotenv import load_dotenv
from gtts import gTTS
from moviepy.editor import AudioFileClip, VideoFileClip
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.generativeai as genai

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

TOPIC_POOL = [
    "interesting space facts",
    "amazing science facts",
    "surprising history facts",
    "mind-blowing nature facts",
    "strange human body facts",
    "unusual technology facts",
    "fun facts about animals",
]


def ensure_dirs() -> Dict[str, Path]:
    output_dir = ROOT / "output"
    audio_dir = output_dir / "audio"
    video_dir = output_dir / "video"
    temp_dir = output_dir / "temp"

    for path in [output_dir, audio_dir, video_dir, temp_dir]:
        path.mkdir(parents=True, exist_ok=True)

    return {
        "output": output_dir,
        "audio": audio_dir,
        "video": video_dir,
        "temp": temp_dir,
    }


def generate_story(topic: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi. .env faylini tekshiring.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    Siz YouTube Shorts uchun qiziqarli, tezkor, 30-50 sekundlik video ssenariysi yozishingiz kerak.
    Mavzu: {topic}

    Talablar:
    1. 30-50 sekund oralig'ida bo'lsin.
    2. O'zbek tilida bo'lsin.
    3. Boshlanishi qiziqarli hook bo'lsin.
    4. 3 qismdan iborat bo'lsin: Hook, asosiy fakt, xulosa.
    5. Matematik yoki sabab-oqibat ma'lumotlar bo'lsin.
    6. Shorts uchun yozilishi kerak.
    7. Har bir jumla qisqa va jozibali bo'lsin.
    8. Yagona JSON obyekti sifatida qaytaring.

    JSON format:
    {{
      "title": "...",
      "description": "...",
      "hashtags": ["...", "..."],
      "script": "...",
      "voiceover_text": "..."
    }}
    """

    response = model.generate_content(prompt)
    content = getattr(response, "text", "")
    if not content:
        raise RuntimeError("Gemini API dan javob olinmadi.")

    return parse_json_response(content)


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Gemini javobi JSON formatida emas.")

    json_text = text[start : end + 1]
    data = json.loads(json_text)

    if "title" not in data or "script" not in data:
        raise ValueError("Gemini javobida kerakli maydonlar yo'q.")

    if "voiceover_text" not in data:
        data["voiceover_text"] = data["script"]

    if "hashtags" not in data or not data["hashtags"]:
        data["hashtags"] = ["shorts", "facts", "youtube"]

    if "description" not in data or not data["description"]:
        data["description"] = "Qiziqarli faktlar va tezkor bilimlar."

    return data


def create_audio_from_text(text: str, output_path: Path) -> None:
    tts = gTTS(text=text, lang="uz", slow=False)
    tts.save(str(output_path))


def fetch_pexels_video(topic: str, output_path: Path) -> str:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        raise ValueError("PEXELS_API_KEY topilmadi. .env faylini tekshiring.")

    url = "https://api.pexels.com/videos/search"
    params = {
        "query": topic,
        "per_page": 5,
        "orientation": "portrait",
        "size": "large",
    }
    headers = {"Authorization": api_key}

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    videos = payload.get("videos", [])
    if not videos:
        raise RuntimeError(f"Pexels API dan {topic} bo'yicha video topilmadi.")

    best_video = None
    for video in videos:
        for file_meta in video.get("video_files", []):
            if file_meta.get("link") and file_meta.get("width", 0) >= 720 and file_meta.get("height", 0) >= 1280:
                if best_video is None:
                    best_video = file_meta
                elif file_meta.get("width", 0) * file_meta.get("height", 0) > best_video.get("width", 0) * best_video.get("height", 0):
                    best_video = file_meta

    if best_video is None:
        best_video = videos[0].get("video_files", [{}])[-1]

    video_url = best_video.get("link")
    if not video_url:
        raise RuntimeError("Pexels videoning download linki topilmadi.")

    with requests.get(video_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    return str(output_path)


def build_shorts_video(background_video_path: Path, audio_path: Path, output_path: Path) -> None:
    video = VideoFileClip(str(background_video_path))
    audio = AudioFileClip(str(audio_path))

    max_duration = min(video.duration, audio.duration, 50)
    video = video.subclip(0, max_duration)
    audio = audio.subclip(0, max_duration)

    target_w, target_h = 1080, 1920
    current_w, current_h = video.size

    if current_w / current_h > target_w / target_h:
        new_w = int(current_h * target_w / target_h)
        x_center = current_w / 2
        x1 = max(0, x_center - (new_w / 2))
        x2 = x1 + new_w
        video = video.crop(x1=x1, y1=0, x2=x2, y2=current_h)
    else:
        new_h = int(current_w * target_h / target_w)
        y_center = current_h / 2
        y1 = max(0, y_center - (new_h / 2))
        y2 = y1 + new_h
        video = video.crop(x1=0, y1=y1, x2=current_w, y2=y2)

    video = video.resize((target_w, target_h))
    video = video.set_audio(audio)
    video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="fast",
        threads=4,
        logger=None,
    )

    video.close()
    audio.close()


def get_youtube_service():
    credentials_path = ROOT / os.getenv("YOUTUBE_CREDENTIALS_FILE", "credentials.json")
    client_secret_path = ROOT / os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secret.json")

    if not client_secret_path.exists():
        raise FileNotFoundError(
            "Google OAuth client_secret.json topilmadi. "
            "Google Cloud Console dan yuklab olib loyiha rootiga qo'ying."
        )

    creds = None
    if credentials_path.exists():
        creds = Credentials.from_authorized_user_file(str(credentials_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(credentials_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path: Path, title: str, description: str, hashtags: List[str]) -> Dict[str, Any]:
    service = get_youtube_service()

    tags = [tag.strip("# ") for tag in hashtags if tag.strip()]
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:15],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": os.getenv("UPLOAD_PRIVACY", "private"),
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=-1,
        resumable=True,
        mimetype="video/mp4",
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = request.execute()
    return response


def run_single_pipeline() -> Dict[str, Any]:
    dirs = ensure_dirs()
    topic = os.getenv("DEFAULT_TOPIC", random.choice(TOPIC_POOL))
    story = generate_story(topic)

    video_name = f"short_{int(time.time())}"
    audio_path = dirs["audio"] / f"{video_name}.mp3"
    bg_video_path = dirs["temp"] / f"{video_name}_bg.mp4"
    final_video_path = dirs["video"] / f"{video_name}.mp4"

    create_audio_from_text(story["voiceover_text"], audio_path)
    fetch_pexels_video(story.get("title", topic), bg_video_path)
    build_shorts_video(bg_video_path, audio_path, final_video_path)

    upload_response = upload_to_youtube(
        final_video_path,
        story["title"],
        story["description"],
        story.get("hashtags", []),
    )

    payload = {
        "topic": topic,
        "story": story,
        "video_path": str(final_video_path),
        "upload_response": upload_response,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main() -> None:
    schedule_time = os.getenv("SCHEDULE_TIME", "18:00")
    schedule.every().day.at(schedule_time).do(run_single_pipeline)

    if os.getenv("RUN_ONCE", "false").lower() == "true":
        run_single_pipeline()
        return

    print(f"Scheduler started. Daily time: {schedule_time}")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Shorts automation script")
    parser.add_argument("--once", action="store_true", help="One-time run instead of scheduler")
    args = parser.parse_args()

    os.environ["RUN_ONCE"] = str(args.once).lower()
    main()
