"""
YouTube Uploader Module
Uploads videos to YouTube using the YouTube Data API v3.
Handles OAuth2 authentication and video metadata.
"""

import os
import json
import logging
import http.client
import httplib2
from pathlib import Path
from typing import Optional

logger = logging.getLogger("uploader")

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    logger.warning("YouTube API libraries not installed")

# OAuth2 scopes required for upload
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE = "youtube"
API_VERSION = "v3"

# Project root for credential storage
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "youtube_token.json"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"


class YouTubeUploader:
    """Handles YouTube video uploads via the Data API v3."""

    def __init__(self, config: dict):
        self.config = config
        self.youtube = None

    def _authenticate(self) -> bool:
        """Authenticate with YouTube using OAuth2."""
        if not YOUTUBE_API_AVAILABLE:
            logger.error("YouTube API libraries not installed")
            return False

        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        credentials = None

        # Check for existing token
        if TOKEN_FILE.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(TOKEN_FILE), SCOPES
                )
                logger.info("Loaded existing YouTube credentials")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                credentials = None

        # Check for environment variable with token JSON
        if not credentials:
            token_json = os.getenv("YOUTUBE_TOKEN_JSON", "")
            if token_json:
                try:
                    token_data = json.loads(token_json)
                    credentials = Credentials.from_authorized_user_info(
                        token_data, SCOPES
                    )
                    logger.info("Loaded YouTube credentials from env var")
                except Exception as e:
                    logger.warning(f"Failed to parse YOUTUBE_TOKEN_JSON: {e}")

        # If no valid credentials, need new OAuth flow
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                logger.info("Refreshed YouTube credentials")
            elif CLIENT_SECRET_FILE.exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRET_FILE), SCOPES
                )
                credentials = flow.run_local_server(port=0)
                logger.info("Completed OAuth2 flow")
            else:
                # Check env for client secret
                client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
                if client_secret:
                    secret_data = json.loads(client_secret)
                    with open(CLIENT_SECRET_FILE, "w") as f:
                        json.dump(secret_data, f)
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CLIENT_SECRET_FILE), SCOPES
                    )
                    credentials = flow.run_local_server(port=0)
                else:
                    logger.error(
                        "No YouTube credentials found. Place client_secret.json "
                        "in credentials/ or set YOUTUBE_CLIENT_SECRET env var."
                    )
                    return False

            # Save token for future use
            with open(TOKEN_FILE, "w") as f:
                f.write(credentials.to_json())

        self.youtube = build(API_SERVICE, API_VERSION, credentials=credentials)
        return True

    def upload(self, video_path: Path, metadata: dict, thumbnail_path: Optional[Path] = None) -> bool:
        """
        Upload a video to YouTube and optionally set a thumbnail.

        Args:
            video_path: Path to the .mp4 file
            metadata: Dict with title, description, tags, category_id, privacy
            thumbnail_path: Optional path to .jpg/png thumbnail

        Returns:
            True if successful, False otherwise
        """
        if not self._authenticate():
            logger.error("Authentication failed, cannot upload")
            return False

        try:
            body = {
                "snippet": {
                    "title": metadata.get("title", "Short automático"),
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", []),
                    "categoryId": metadata.get("category_id", "22"), # People & Blogs or Science/Tech
                },
                "status": {
                    "privacyStatus": metadata.get("privacy", "public"),
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                resumable=True
            )

            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            logger.info(f"Uploading video: {video_path.name}")
            response = request.execute()
            video_id = response.get("id")
            logger.info(f"✅ Video uploaded! ID: {video_id}")

            if thumbnail_path and video_id:
                self.set_thumbnail(video_id, thumbnail_path)

            return True

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False

    def set_thumbnail(self, video_id: str, thumbnail_path: Path):
        """Set a custom thumbnail for a video."""
        try:
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path))
            )
            request.execute()
            logger.info(f"✅ Thumbnail set for {video_id}")
        except Exception as e:
            logger.error(f"Failed to set thumbnail: {e}")

    def check_quota(self) -> dict:
        """Check remaining YouTube API quota (informational)."""
        # YouTube Data API has a default quota of 10,000 units/day
        # A video upload costs 1600 units
        # So: ~6 uploads per day on free tier
        return {
            "daily_quota": 10000,
            "upload_cost": 1600,
            "max_uploads_per_day": 6,
            "note": "YouTube Data API v3 free tier limits",
        }

if __name__ == "__main__":
    import sys
    # Add logging handler for console output
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    logger.info("Testing YouTube Uploader Authentication...")
    
    try:
        uploader = YouTubeUploader({})
        success = uploader._authenticate()
        if success:
            logger.info("Authentication successful! Token saved in credentials/youtube_token.json")
        else:
            logger.error("Authentication failed.")
    except Exception as e:
        logger.error(f"Authentication exception: {e}")
