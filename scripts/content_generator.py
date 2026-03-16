import os
import logging
from pathlib import Path
from typing import Optional, List
from google import genai
from gtts import gTTS

logger = logging.getLogger("content_generator")

class ContentGenerator:
    """Generates original video scripts using Gemini and voiceovers using gTTS."""

    def __init__(self, config: dict):
        self.config = config
        self.api_key = os.getenv("GOOGLE_API_KEY") # User needs to have this in Secrets
        if not self.api_key:
            # Fallback for local testing if env not set, but expected in GitHub Actions
            logger.warning("GOOGLE_API_KEY not found in environment.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-1.5-flash"

    def generate_content(self, topic: str):
        """Generates a script and search keywords for a given topic."""
        logger.info(f"Generating script for topic: {topic}")
        
        prompt = f"""
        Write a high-energy, fast-paced YouTube Shorts script about: {topic}.
        The script must be exactly 50 words long.
        Do not use emojis, do not use complex formatting.
        Topic context: Global Audiovisual Insights (AV technology, monitors, projectors).
        Include a hook at the beginning and a call to action at the end.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            script = response.text.strip()
            logger.info("Script generated successfully.")
            
            # Extract keywords for Pexels search
            keyword_prompt = f"Extract 3 simple English keywords for stock video search from this script, separated by commas: {script}"
            kw_response = self.client.models.generate_content(
                model=self.model_id,
                contents=keyword_prompt
            )
            keywords = [k.strip() for k in kw_response.text.split(",")]
            logger.info(f"Keywords extracted: {keywords}")
            
            return {
                "script": script,
                "keywords": keywords,
                "topic": topic
            }
        except Exception as e:
            logger.error(f"Error generating AI content: {e}")
            return None

    def generate_voiceover(self, text: str, output_path: Path) -> Optional[Path]:
        """Convert text to speech and save as MP3."""
        logger.info(f"Generating voiceover: {output_path}")
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(str(output_path))
            return output_path
        except Exception as e:
            logger.error(f"Error generating voiceover: {e}")
            return None
