import os
import subprocess
import logging
from pathlib import Path

from typing import Optional

logger = logging.getLogger("assets")

class AssetManager:
    """Handles downloading and managing video assets."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "assets" / "raw_videos"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def download_video(self, video_id: str) -> Optional[Path]:
        """Download video in best quality using yt-dlp."""
        output_tmpl = str(self.raw_dir / f"{video_id}.%(ext)s")
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        logger.info(f"Downloading video {video_id}...")
        
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "--merge-output-format", "mp4",
            "-o", output_tmpl,
            url
        ]
        
        try:
            subprocess.run(cmd, check=True)
            # Find the actual file (could be .mp4)
            for file in self.raw_dir.glob(f"{video_id}.*"):
                if file.suffix == ".mp4":
                    return file
            return None
        except Exception as e:
            logger.error(f"Error downloading video {video_id}: {e}")
            return None
