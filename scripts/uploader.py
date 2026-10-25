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
                
                print(f"\n{'='*60}")
                print("MÉTODO DE EMERGENCIA (Si localhost falla):")
                print("1. Abre este link en tu navegador:")
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                print(auth_url)
                print("\n2. Elige tu cuenta y acepta.")
                print("3. La página dará ERROR (localhost rechazó la conexión). ¡NO PASA NADA!")
                print("4. MIRA LA BARRA DE DIRECCIONES de tu navegador (donde pone la URL).")
                print("5. Verás algo como: http://localhost:8080/?code=4/0Af...&scope=...")
                print("6. COPIA todo lo que hay DESPUÉS de 'code=' y ANTES de '&scope='.")
                print(f"{'='*60}\n")
                
                try:
                    logger.info("Intentando abrir servidor local en 127.0.0.1:8080...")
                    credentials = flow.run_local_server(
                        host='127.0.0.1',
                        port=8080, 
                        prompt='consent',
                        timeout_seconds=60,
                        success_message='Autorización completada. Ya puedes cerrar esta ventana.'
                    )
                except Exception as e:
                    logger.warning(f"No se pudo iniciar el servidor local: {e}")
                    print("\n[MODO MANUAL ACTIVADO]")
                    code = input("Pega aquí el código que aparece en la URL del navegador despues de 'code=': ").strip()
                    flow.fetch_token(code=code)
                    credentials = flow.credentials
                
                logger.info("Completed OAuth2 flow")
            else:
                logger.error(
                    "No YouTube credentials found. Please ensure credentials/client_secret.json exists."
                )
                return False

            # Save token for future use
            with open(TOKEN_FILE, "w") as f:
                f.write(credentials.to_json())

        self.youtube = build(API_SERVICE, API_VERSION, credentials=credentials)
        return True

    @staticmethod
    def sanitize_tags(tags: list, max_total_chars: int = 400) -> list:
        """
        Sanitize tags according to YouTube rules:
        - No quotes, angle brackets, newlines, or internal commas
        - Strip leading '#'
        - Limit tag length to 80 chars
        - YouTube wraps tags containing spaces in quotes, adding 2 chars to total budget
        - Total serialized budget capped at max_total_chars (<= 400, well below 500 limit)
        """
        if not tags:
            return []
        cleaned = []
        seen = set()
        total_len = 0
        for item in tags:
            if not item or not isinstance(item, str):
                continue
            # Strip forbidden characters: <, >, quotes, newlines, #, commas
            t = (item.replace('<', '')
                     .replace('>', '')
                     .replace('"', '')
                     .replace("'", '')
                     .replace('\n', ' ')
                     .replace('\r', ' ')
                     .replace('#', '')
                     .replace(',', ' ')
                     .strip())
            t = " ".join(t.split())
            if not t:
                continue
            t = t[:80].strip()
            t_lower = t.lower()
            if t_lower in seen:
                continue

            # YouTube counts multi-word tags as wrapped in quotes: "word word" (+2 chars)
            tag_cost = len(t) + (2 if ' ' in t else 0)
            sep_cost = 1 if cleaned else 0

            if total_len + sep_cost + tag_cost <= max_total_chars:
                cleaned.append(t)
                total_len += sep_cost + tag_cost
                seen.add(t_lower)
            else:
                break
        return cleaned

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

        safe_tags = self.sanitize_tags(metadata.get("tags", []))
        category_id = str(metadata.get("category_id") or self.config.get("seo", {}).get("category_id", "28"))
        privacy_status = metadata.get("privacy") or self.config.get("seo", {}).get("privacy", "public")

        body = {
            "snippet": {
                "title": metadata.get("title", "Short automático")[:100],
                "description": metadata.get("description", "")[:5000],
                "tags": safe_tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
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

        except HttpError as e:
            error_str = str(e)
            if "invalidTags" in error_str or "invalid video keywords" in error_str.lower():
                logger.warning(f"YouTube rejected tags ({error_str}). Retrying upload with emergency safe tags...")
                try:
                    body["snippet"]["tags"] = ["GlobalAVInsights", "Shorts"]
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
                    response = request.execute()
                    video_id = response.get("id")
                    logger.info(f"✅ Video uploaded successfully on retry! ID: {video_id}")

                    if thumbnail_path and video_id:
                        self.set_thumbnail(video_id, thumbnail_path)

                    return True
                except Exception as retry_e:
                    logger.error(f"Upload retry failed: {retry_e}")
                    return False
            else:
                logger.error(f"Upload failed: {e}")
                return False
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
