"""
YouTube Shorts Automation — GlobalAVInsights
Main Orchestrator: Select → Download → Edit → Thumbnail → SEO → Upload
"""

import os
import sys
import yaml
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.channel_manager import ChannelManager
from scripts.assets import AssetManager
from scripts.video_builder import VideoBuilder
from scripts.seo import SEOGenerator
from scripts.thumbnail_generator import ThumbnailGenerator
from scripts.uploader import YouTubeUploader

# --- Logging ---
_log_handlers = [logging.StreamHandler()]
try:
    os.makedirs(PROJECT_ROOT / "output", exist_ok=True)
    _log_handlers.append(
        logging.FileHandler(PROJECT_ROOT / "output" / "pipeline.log", encoding="utf-8")
    )
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger("main")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config.yml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["PROJECT_ROOT"] = str(PROJECT_ROOT)
    return cfg


def should_run(history: dict, interval_hours: int = 6) -> bool:
    videos = history.get("videos", [])
    if not videos:
        return True
    last_ts = videos[-1].get("timestamp", "")
    if not last_ts:
        return True
    try:
        last_upload = datetime.strptime(last_ts, "%Y%m%d_%H%M%S")
        return datetime.now() >= last_upload + timedelta(hours=interval_hours)
    except ValueError:
        return True


def run_pipeline():
    logger.info("=" * 60)
    logger.info("🚀 GlobalAVInsights — YouTube Shorts Automation")
    logger.info("=" * 60)

    config = load_config()
    channel_url = config["channel"]["url"]
    interval = config["schedule"]["interval_hours"]

    # --- Setup ---
    os.makedirs(PROJECT_ROOT / "output" / "videos", exist_ok=True)
    os.makedirs(PROJECT_ROOT / "output" / "thumbnails", exist_ok=True)
    os.makedirs(PROJECT_ROOT / "assets" / "raw_videos", exist_ok=True)

    history_path = str(PROJECT_ROOT / "output" / "history.json")
    manager = ChannelManager(channel_url, history_file=history_path)
    history = manager.load_history()

    # --- Check Schedule ---
    if not should_run(history, interval):
        logger.info("⏳ Skipping — next upload not due yet.")
        return

    # --- Phase 1: Select Video ---
    logger.info("📋 Phase 1: Selecting best video from channel...")
    video_meta = manager.select_best_video()
    if not video_meta:
        logger.error("❌ No eligible video found.")
        return
    logger.info(f"✅ Selected: {video_meta['title']} ({video_meta['views']} views)")

    # --- Phase 2: Download ---
    logger.info("⬇️ Phase 2: Downloading video...")
    asset_mgr = AssetManager(config["PROJECT_ROOT"])
    raw_path = asset_mgr.download_video(video_meta["id"])
    if not raw_path:
        logger.error("❌ Failed to download video.")
        return
    logger.info(f"✅ Downloaded: {raw_path}")

    # --- Phase 3: Build Short ---
    logger.info("🎬 Phase 3: Building Short (9:16, 55s, subtitles, fadeout)...")
    builder = VideoBuilder(config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_path = PROJECT_ROOT / "output" / "videos" / f"short_{timestamp}.mp4"
    builder.build_short(raw_path, short_path)
    logger.info(f"✅ Short rendered: {short_path}")

    # --- Phase 4: Thumbnail ---
    logger.info("🖼️ Phase 4: Generating thumbnail...")
    thumb_path = PROJECT_ROOT / "output" / "thumbnails" / f"thumb_{timestamp}.jpg"
    thumb_gen = ThumbnailGenerator(config)
    # Use first 3 words of title as thumbnail text
    thumb_text = " ".join(video_meta["title"].split()[:3]).upper()
    thumb_gen.generate(short_path, thumb_path, text=thumb_text)
    logger.info(f"✅ Thumbnail: {thumb_path}")

    # --- Phase 5: SEO ---
    logger.info("🔍 Phase 5: Generating SEO metadata...")
    seo = SEOGenerator(config)
    original_url = f"https://www.youtube.com/watch?v={video_meta['id']}"
    metadata = seo.generate(video_meta["title"], original_url)
    logger.info(f"✅ Title: {metadata['title']}")

    # Save metadata
    meta_path = short_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # --- Phase 6: Upload ---
    if os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").lower() == "true":
        logger.info("📤 Phase 6: Uploading to YouTube...")
        uploader = YouTubeUploader(config)
        success = uploader.upload(short_path, metadata, thumb_path)
        if success:
            manager.mark_as_processed(video_meta["id"])
            logger.info("🎉 Short published successfully!")
        else:
            logger.error("❌ Upload failed.")
    else:
        logger.info("⏭️ Phase 6: Upload SKIPPED (set YOUTUBE_UPLOAD_ENABLED=true)")

    # --- Update History ---
    history["videos"].append({
        "timestamp": timestamp,
        "video_id": video_meta["id"],
        "original_title": video_meta["title"],
        "short_path": str(short_path),
        "metadata": metadata,
    })
    manager.save_history(history)

    logger.info("=" * 60)
    logger.info("🎉 Pipeline complete!")
    logger.info(f"📁 Short: {short_path}")
    logger.info(f"🖼️ Thumb: {thumb_path}")
    logger.info(f"📋 Meta:  {meta_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)
