import os
import subprocess
import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger("channel_manager")


class ChannelManager:
    """Manages video selection and metadata extraction for @GlobalAVInsights."""

    def __init__(self, channel_url: str, history_file: str = "output/history.json"):
        self.channel_url = channel_url
        self.history_file = history_file
        self._ensure_history()

    def _ensure_history(self):
        os.makedirs(os.path.dirname(self.history_file) or ".", exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({"videos": [], "topics_used": [], "processed_ids": []}, f)

    def load_history(self):
        with open(self.history_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_history(self, history):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def get_eligible_videos(self, limit: int = 10):
        """Fetch video list from channel using yt-dlp, writing to temp file for reliability."""
        url = self.channel_url.rstrip('/') + '/videos'
        logger.info(f"Fetching videos from {url}...")

        # Write JSON to a temp file to avoid Windows subprocess encoding issues
        tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        tmp_path = tmp_file.name
        tmp_file.close()

        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-single-json",
            "--playlist-items", f"1-{limit}",
            "--no-warnings",
            "-o", "-",  # not needed for dump-json but harmless
            url
        ]

        try:
            # Use shell redirection to write output to temp file
            full_cmd = f'yt-dlp --flat-playlist --dump-single-json --playlist-items 1-{limit} --no-warnings "{url}" > "{tmp_path}"'
            subprocess.run(full_cmd, shell=True, check=True, timeout=120)

            with open(tmp_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)

            entries = data.get("entries", [])
            videos = []
            for entry in entries:
                vid_id = entry.get("id", "")
                title = entry.get("title", "Unknown")
                views = entry.get("view_count") or 0
                date = entry.get("upload_date", "")
                duration = entry.get("duration") or 0

                # Skip existing Shorts (< 61 seconds)
                if duration and duration < 61:
                    logger.info(f"  Skipping Short: {title} ({duration}s)")
                    continue

                videos.append({
                    "id": vid_id,
                    "title": title,
                    "description": entry.get("description", ""),
                    "views": int(views),
                    "date": date,
                    "duration": duration,
                })
                logger.info(f"  Found: {title} ({views} views, {duration}s)")

            logger.info(f"Total eligible long-form videos: {len(videos)}")
            return videos

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timed out fetching channel videos")
            return []
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

    def select_best_video(self):
        """Select a video based on view count among those not yet processed."""
        history = self.load_history()
        processed_ids = history.get("processed_ids", [])

        videos = self.get_eligible_videos(limit=20)
        unprocessed = [v for v in videos if v['id'] not in processed_ids]

        if not unprocessed:
            logger.warning("No new unprocessed videos found! RECYCLING history to keep producing shorts.")
            # Clear processed history
            history["processed_ids"] = []
            self.save_history(history)
            # Re-select from the full pool
            unprocessed = videos

        # Sort by views (descending) to pick highest impact
        unprocessed.sort(key=lambda x: x['views'], reverse=True)
        selected = unprocessed[0]
        logger.info(f"Selected: '{selected['title']}' ({selected['views']} views)")
        return selected

    def mark_as_processed(self, video_id: str):
        history = self.load_history()
        if "processed_ids" not in history:
            history["processed_ids"] = []
        if video_id not in history["processed_ids"]:
            history["processed_ids"].append(video_id)
            self.save_history(history)

    def get_video_metadata(self, video_id: str) -> dict:
        """Fetch detailed metadata (title, description, tags) for a specific video."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Fetching deep metadata for {url}...")
        
        tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        tmp_path = tmp_file.name
        tmp_file.close()

        cmd = f'yt-dlp --dump-json --no-warnings "{url}" > "{tmp_path}"'
        
        try:
            subprocess.run(cmd, shell=True, check=True, timeout=60)
            with open(tmp_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
                
            return {
                "id": data.get("id"),
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "tags": data.get("tags", [])
            }
        except Exception as e:
            logger.error(f"Error fetching metadata for {video_id}: {e}")
            return {
                "id": video_id,
                "title": "",
                "description": "",
                "tags": []
            }
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

