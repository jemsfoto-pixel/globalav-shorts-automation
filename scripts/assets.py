"""
Asset Fetcher Module — PRO Version
Downloads free stock VIDEOS and images from Pexels API for video backgrounds.
Prioritizes vertical video clips for maximum engagement.
Falls back to images, then solid-color backgrounds.
"""

import os
import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger("assets")


class AssetFetcher:
    """Downloads visual assets (videos + images) from Pexels."""

    def __init__(self, config: dict):
        self.config = config
        self.api_key = os.getenv(config["apis"]["pexels"]["env_var"], "")
        self.per_video = config["apis"]["pexels"].get("per_video", 5)
        self.base_url_photos = "https://api.pexels.com/v1"
        self.base_url_videos = "https://api.pexels.com/videos"

    def fetch_for_script(self, script: dict, output_dir: Path) -> list:
        """
        Fetch video clips (preferred) or images for each segment.
        Returns list of asset dicts with paths and types.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        video_dir = output_dir.parent / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        assets = []

        for i, segment in enumerate(script.get("segments", [])):
            query = segment.get("visual_description", "technology")

            # Try VIDEO first, fall back to IMAGE
            video_path = self._fetch_video(query, video_dir, index=i)
            if video_path:
                assets.append({
                    "path": str(video_path),
                    "type": "video",
                    "segment_index": i,
                    "query": query,
                })
                logger.info(f"✅ Video clip {i}: {video_path.name}")
            else:
                image_path = self._fetch_image(query, output_dir, index=i)
                assets.append({
                    "path": str(image_path) if image_path else None,
                    "type": "image" if image_path else None,
                    "segment_index": i,
                    "query": query,
                })

        return assets

    def _fetch_video(self, query: str, output_dir: Path, index: int) -> Optional[Path]:
        """Fetch a short video clip from Pexels Videos API."""
        if not self.api_key:
            return None

        try:
            clean_query = self._clean_query(query)
            headers = {"Authorization": self.api_key}
            params = {
                "query": clean_query,
                "per_page": 5,
                "orientation": "portrait",
                "size": "small",
            }

            response = requests.get(
                f"{self.base_url_videos}/search",
                headers=headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            videos = data.get("videos", [])
            if not videos:
                logger.info(f"No videos found for: {clean_query}, trying images")
                return None

            # Find the best video file (prefer HD, vertical, short duration)
            for video in videos:
                duration = video.get("duration", 0)
                if duration > 30:  # Skip videos longer than 30 seconds
                    continue

                video_files = video.get("video_files", [])
                best_file = self._pick_best_video_file(video_files)

                if best_file:
                    video_url = best_file["link"]
                    filename = f"clip_{index:03d}_{hashlib.md5(query.encode()).hexdigest()[:8]}.mp4"
                    filepath = output_dir / filename

                    if filepath.exists():
                        logger.info(f"Video cached: {filename}")
                        return filepath

                    # Download video
                    vid_response = requests.get(video_url, timeout=60, stream=True)
                    vid_response.raise_for_status()

                    with open(filepath, "wb") as f:
                        for chunk in vid_response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    size_kb = filepath.stat().st_size // 1024
                    logger.info(f"Downloaded video: {filename} ({size_kb}KB)")
                    return filepath

            return None

        except requests.RequestException as e:
            logger.error(f"Failed to fetch video for '{query}': {e}")
            return None

    def _pick_best_video_file(self, video_files: list) -> Optional[dict]:
        """Pick the best quality vertical video file."""
        # Prefer: HD quality, vertical aspect ratio
        candidates = []
        for vf in video_files:
            width = vf.get("width", 0)
            height = vf.get("height", 0)
            quality = vf.get("quality", "")

            # Prefer vertical or square videos
            if height >= width and quality in ("hd", "sd"):
                candidates.append({
                    **vf,
                    "score": (2 if quality == "hd" else 1) + (1 if height >= 1080 else 0)
                })

        # If no vertical, take any HD
        if not candidates:
            for vf in video_files:
                quality = vf.get("quality", "")
                if quality in ("hd", "sd"):
                    candidates.append({**vf, "score": 1 if quality == "hd" else 0})

        if candidates:
            candidates.sort(key=lambda x: x["score"], reverse=True)
            return candidates[0]

        return video_files[0] if video_files else None

    def _fetch_image(self, query: str, output_dir: Path, index: int) -> Optional[Path]:
        """Fetch a single image from Pexels (fallback when no video found)."""
        if not self.api_key:
            logger.info(f"No Pexels API key, skipping fetch for: {query}")
            return None

        try:
            clean_query = self._clean_query(query)
            headers = {"Authorization": self.api_key}
            params = {
                "query": clean_query,
                "per_page": 3,
                "orientation": "portrait",
                "size": "medium",
            }

            response = requests.get(
                f"{self.base_url_photos}/search",
                headers=headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            photos = data.get("photos", [])
            if not photos:
                logger.warning(f"No images found for: {clean_query}")
                return None

            photo = photos[0]
            image_url = photo["src"]["large2x"]

            filename = f"asset_{index:03d}_{hashlib.md5(query.encode()).hexdigest()[:8]}.jpg"
            filepath = output_dir / filename

            if filepath.exists():
                logger.info(f"Image cached: {filename}")
                return filepath

            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(img_response.content)

            logger.info(f"Downloaded: {filename} ({len(img_response.content) // 1024}KB)")
            return filepath

        except requests.RequestException as e:
            logger.error(f"Failed to fetch image for '{query}': {e}")
            return None

    def _clean_query(self, description: str) -> str:
        """Extract key search terms and translate basic Spanish tech terms to English."""
        # Pexels search works much better in English
        translations = {
            "inteligencia": "artificial intelligence",
            "artificial": "ai",
            "tecnología": "technology",
            "herramientas": "software tools",
            "gratis": "free",
            "automatización": "automation",
            "finanzas": "finance",
            "dinero": "money",
            "invertir": "investing",
            "ahorro": "saving",
            "criptomonedas": "crypto",
            "datos": "data",
            "ciencia": "science",
            "futuro": "future",
            "robot": "robot",
            "libro": "books",
            "libros": "books",
            "resumen": "reading",
            "lectura": "reading",
        }
        
        stop_words = {
            "imagen", "de", "del", "la", "el", "los", "las", "un", "una",
            "con", "para", "por", "que", "como", "sobre", "o", "y", "en",
            "abstracta", "relacionada", "impactante", "animado", "animada",
        }
        
        words = description.lower().split()
        filtered = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Translate key terms to English for better Pexels results
        translated = []
        for w in filtered:
            # Check for direct translations or partial matches
            for span, eng in translations.items():
                if span in w:
                    translated.append(eng)
                    break
            else:
                translated.append(w)
                
        result = " ".join(translated[:3])  # Max 3 keywords for Pexels to keep search broad
        return result if result else "technology ai"


class ColorBackgroundGenerator:
    """Generates solid/gradient color backgrounds as fallback."""

    def __init__(self, config: dict):
        self.video_config = config["video"]

    def generate(self, color: str, output_path: Path) -> Path:
        """Generate a solid color image for use as background."""
        try:
            from PIL import Image, ImageDraw

            width = self.video_config["width"]
            height = self.video_config["height"]

            img = Image.new("RGB", (width, height), color)
            draw = ImageDraw.Draw(img)
            for y in range(height):
                alpha = int(40 * (y / height))
                draw.line(
                    [(0, y), (width, y)],
                    fill=(alpha, alpha, alpha),
                )

            img.save(str(output_path), quality=95)
            logger.info(f"Generated background: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate background: {e}")
            return output_path
