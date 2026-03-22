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
        self.api_key = os.getenv("GOOGLE_API_KEY", "").strip() # User needs to have this in Secrets
        if not self.api_key:
            # Fallback for local testing if env not set, but expected in GitHub Actions
            logger.warning("GOOGLE_API_KEY not found in environment.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-flash-latest"

    def generate_content(self, topic: str):
        """Generates a script and search keywords for a given topic."""
        logger.info(f"Generating script for topic: {topic}")
        
        prompt = f"""
        Actúa como un creador de YouTube Shorts viral.
        Escribe un guion dinámico y de ritmo rápido en ESPAÑOL sobre: {topic}.
        El guion debe tener exactamente 50-60 palabras para durar unos 45 segundos.
        NO USES emojis, ni formatos complejos (ni asteriscos, ni negritas, ni comillas). Solo texto plano continuo.
        Contexto del canal: Global Audiovisual Insights (tecnología AV, monitores, proyectores, sonido, home theater).
        Incluye un "gancho" inicial muy atractivo en la primera frase y una llamada a la acción rápida al final pidiendo suscripción.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            script = response.text.strip().replace("\n", " ").replace("*", "")
            logger.info("Script generated successfully.")
            
            # Extract keywords for Pexels search
            keyword_prompt = f"Read the following Spanish script and extract exactly 3 simple English keywords for stock video search, separated by commas (e.g., monitor, technology, office): {script}"
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

    def generate_topics(self, count: int = 5) -> List[str]:
        """Generates a list of new and trending topics for the AV niche."""
        logger.info(f"Generating {count} new topics for the AV channel...")
        
        prompt = f"""
        Actúa como un estratega de contenido para un canal de YouTube sobre tecnología Audiovisual (AV).
        Genera una lista de {count} temas de actualidad y tendencia (trending topics) en ESPAÑOL para YouTube Shorts.
        Enfócate en: monitores (OLED, Gaming), proyectores, sonido de alta fidelidad (Hi-Fi), noticias tecnológicas, comparativas rápidas o consejos de configuración.
        Devuelve SOLO la lista de temas, uno por línea, sin números ni guiones.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            topics = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
            logger.info(f"Successfully generated topics: {topics}")
            return topics[:count]
        except Exception as e:
            logger.error(f"Error generating topics: {e}")
            return []

    def generate_voiceover(self, text: str, output_path: Path) -> Optional[Path]:
        """Convert text to speech and save as MP3."""
        logger.info(f"Generating voiceover: {output_path}")
        try:
            tts = gTTS(text=text, lang='es', tld='es', slow=False)
            tts.save(str(output_path))
            return output_path
        except Exception as e:
            logger.error(f"Error generating voiceover: {e}")
            return None
