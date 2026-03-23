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

def run_clip_pipeline(config, manager, history, timestamp):
    logger.info("🎬 Mode: EXPLAINER PIPELINE (YouTube long-form explained by AI)")
    
    # --- Phase 1: Select Video ---
    logger.info("📋 Phase 1: Selecting best video from channel...")
    video_meta_basic = manager.select_best_video()
    if not video_meta_basic:
        logger.error("❌ No eligible video found for explaining.")
        return False

    logger.info(f"✅ Selected: {video_meta_basic['title']} ({video_meta_basic['views']} views)")

    # Fetch full metadata to get description (use basic metadata as fallback if yt-dlp is blocked)
    video_meta = manager.get_video_metadata(video_meta_basic['id'], fallback_title=video_meta_basic['title'], fallback_desc=video_meta_basic.get('description', ''))
    
    from scripts.content_generator import ContentGenerator
    gen = ContentGenerator(config)
    
    # --- Phase 2: Generate Content from Video ---
    logger.info("🧠 Phase 2: Generating explanation script from video metadata...")
    content = gen.generate_content_from_video(video_meta["title"], video_meta.get("description", ""))
    
    if not content:
        logger.error("❌ Failed to generate explainer script.")
        return False

    short_path = Path(config["PROJECT_ROOT"]) / "output" / "videos" / f"short_{timestamp}.mp4"
    
    # --- Phase 3: Audio & Stock Footage ---
    from scripts.assets import AssetManager
    asset_mgr = AssetManager(config)
    audio_path = Path(config["PROJECT_ROOT"]) / "assets" / "raw_videos" / f"voice_{timestamp}.mp3"
    
    logger.info("🔊 Generating voiceover...")
    gen.generate_voiceover(content["script"], audio_path)
    
    logger.info(f"🔍 Searching Pexels for: {content['keywords']}")
    video_paths = asset_mgr.download_pexels_videos(content["keywords"])
    
    if not video_paths:
        logger.error("❌ Failed to download stock footage.")
        return False
    
    # --- Phase 4: Build Generative Short ---
    logger.info("🎬 Phase 4: Building Generative Explainer Short...")
    builder = VideoBuilder(config)
    try:
        builder.build_generative_short(audio_path, video_paths, short_path, content["script"])
    except Exception as e:
        logger.error(f"❌ Failed to build AI short: {e}")
        return False
    
    # --- Phase 5: SEO & Metadata ---
    logger.info("🔍 Phase 5: Generating SEO metadata...")
    seo = SEOGenerator(config)
    original_url = f"https://www.youtube.com/watch?v={video_meta['id']}"
    # Use dynamic generator
    metadata = seo.generate(video_meta["title"], original_url)
    thumb_text = " ".join(video_meta["title"].split()[:3]).upper()
    
    return process_post_generation(config, manager, history, timestamp, short_path, thumb_text, metadata, video_meta["id"], video_meta["title"])


def run_ai_pipeline(config, manager, history, timestamp):
    logger.info("🧠 Mode: AI GENERATIVE PIPELINE")
    gen_config = config.get("generator", {})
    if not gen_config.get("enabled"):
        logger.error("❌ Generator is disabled in config.")
        return False
        
    from scripts.content_generator import ContentGenerator
    import random
    
    gen = ContentGenerator(config)
    
    # --- Topic Selection Logic ---
    static_topics = gen_config.get("topics", ["Tecnología Audiovisual"])
    used_topics = history.get("topics_used", [])
    
    # Filter available topics
    available_topics = [t for t in static_topics if t not in used_topics]
    
    if not available_topics:
        logger.info("🔄 Static topics exhausted or variety needed. Generating dynamic topics...")
        dynamic_topics = gen.generate_topics(count=5)
        # Filter dynamic topics too (just in case they were generated/used before)
        available_topics = [t for t in dynamic_topics if t not in used_topics]
        
        # If still nothing (rare), just pick from dynamic or fallback
        if not available_topics:
            available_topics = dynamic_topics if dynamic_topics else [random.choice(static_topics)]

    topic = random.choice(available_topics)
    logger.info(f"🎯 Selected Topic: {topic}")
    
    short_path = Path(config["PROJECT_ROOT"]) / "output" / "videos" / f"short_{timestamp}.mp4"
    
    # 1. Script & Keywords
    content = gen.generate_content(topic)
    if not content:
        logger.error("❌ Failed to generate AI content.")
        return False
    
    # 2. Audio
    asset_mgr = AssetManager(config)
    audio_path = Path(config["PROJECT_ROOT"]) / "assets" / "raw_videos" / f"voice_{timestamp}.mp3"
    gen.generate_voiceover(content["script"], audio_path)
    
    # 3. Stock Footage
    logger.info(f"🔍 Searching Pexels for: {content['keywords']}")
    video_paths = asset_mgr.download_pexels_videos(content["keywords"])
    if not video_paths:
        logger.error("❌ Failed to download stock footage.")
        return False
    
    # 4. Build Generative Short
    logger.info("🎬 Phase 3: Building Generative Short...")
    builder = VideoBuilder(config)
    try:
        builder.build_generative_short(audio_path, video_paths, short_path, content["script"])
    except Exception as e:
        logger.error(f"❌ Failed to build AI short: {e}")
        return False
    
    # 5. Metadata
    thumb_text = topic.upper()
    metadata = {
        "title": f"¡{topic}! #Shorts #AV",
        "description": f"Perspectivas de IA sobre {topic}. \n\n{content['script']}",
        "tags": content["keywords"] + ["AV", "Shorts", "GlobalAVInsights"]
    }
    
    # Mark topic as used in history
    if "topics_used" not in history:
        history["topics_used"] = []
    history["topics_used"].append(topic)
    
    return process_post_generation(config, manager, history, timestamp, short_path, thumb_text, metadata, "generative", f"AI: {topic}")


def process_post_generation(config, manager, history, timestamp, short_path, thumb_text, metadata, video_id, original_title):
    logger.info(f"✅ Short ready: {short_path}")

    # --- Phase 5: Thumbnail ---
    logger.info("🖼️ Phase 5: Generating thumbnail...")
    thumb_path = Path(config["PROJECT_ROOT"]) / "output" / "thumbnails" / f"thumb_{timestamp}.jpg"
    thumb_gen = ThumbnailGenerator(config)
    thumb_gen.generate(short_path, thumb_path, text=thumb_text)
    logger.info(f"✅ Thumbnail: {thumb_path}")

    # Save metadata
    logger.info(f"✅ Title: {metadata['title']}")
    meta_path = short_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # --- Phase 6: Upload ---
    if os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").lower() == "true":
        logger.info("📤 Phase 6: Uploading to YouTube...")
        uploader = YouTubeUploader(config)
        success = uploader.upload(short_path, metadata, thumb_path)
        if success:
            if video_id != "generative":
                manager.mark_as_processed(video_id)
            logger.info("🎉 Short published successfully!")
        else:
            logger.error("❌ Upload failed.")
    else:
        logger.info("⏭️ Phase 6: Upload SKIPPED (set YOUTUBE_UPLOAD_ENABLED=true)")

    # --- Update History ---
    history["videos"].append({
        "timestamp": timestamp,
        "video_id": video_id,
        "original_title": original_title,
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determine which pipeline to run
    # Defaults to 'auto'. 'auto' means try clip, then try AI if clip fails (no videos left).
    pipeline_mode = os.getenv("PIPELINE_MODE", "auto").lower()

    if pipeline_mode == "clip":
        run_clip_pipeline(config, manager, history, timestamp)
    elif pipeline_mode == "ai":
        run_ai_pipeline(config, manager, history, timestamp)
    else: # auto
        logger.info("🔄 Mode: AUTO. Attempting CLIP pipeline first...")
        success = run_clip_pipeline(config, manager, history, timestamp)
        if not success:
            logger.info("🔄 CLIP pipeline skipped or failed. Falling back to AI pipeline...")
            run_ai_pipeline(config, manager, history, timestamp)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)
