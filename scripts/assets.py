import os
import subprocess
import logging
from pathlib import Path

import requests
from typing import Optional, List

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
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--extractor-args", "youtube:player_client=android,web;player_skip=web_embedded",
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

    def download_pexels_videos(self, keywords: List[str], count: int = 3) -> List[Path]:
        """Search and download vertical videos from Pexels."""
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            logger.error("PEXELS_API_KEY not found.")
            return []

        downloaded = []
        headers = {"Authorization": api_key}
        
        # We'll use the first 2 keywords for better search variety
        query = " ".join(keywords[:2])
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page={count}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for i, video in enumerate(data.get("videos", [])):
                video_files = video.get("video_files", [])
                best_file = next((f for f in video_files if f["quality"] == "hd"), video_files[0])
                file_url = best_file["link"]
                
                dest = self.raw_dir / f"pexels_{i}_{video['id']}.mp4"
                logger.info(f"Downloading Pexels clip: {file_url}")
                
                with requests.get(file_url, stream=True) as r:
                    r.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                downloaded.append(dest)
                if len(downloaded) >= count:
                    break
                    
            return downloaded
        except Exception as e:
            logger.error(f"Error fetching Pexels videos: {e}")
            return downloaded
