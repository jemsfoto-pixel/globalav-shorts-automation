import logging
import os
from typing import Optional

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger("seo")

class SEOGenerator:
    """Generates optimized metadata for YouTube Shorts."""

    def __init__(self, config: dict):
        self.config = config
        self.client = None
        if GEMINI_AVAILABLE:
            api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if api_key:
                self.client = genai.Client(api_key=api_key)

    def generate(self, original_title: str, video_url: str) -> dict:
        """Create title and description based on original video context."""
        
        short_title = f"¡Descubre esto! 🔊 {original_title[:30]} #Shorts"
        description = (
            f"Mira el video completo aquí: {video_url}\n\n"
            "Suscríbete para más tips de calibración y pruebas de sonido de alta fidelidad. "
            "#GlobalAVInsights #Shorts #HiFi #Audio"
        )
        tags = ["Shorts", "GlobalAVInsights", "HiFi", "Audio", "Tecnología"]
        
        if self.client:
            try:
                prompt = f"""
                Genera metadatos SEO virales para un YouTube Short en español sobre este tema:
                TEMA: {original_title}
                
                Devuelve exactamente tres líneas y NADA MÁS. NINGUNA disculpa ni aclaración:
                1. Un título muy gancho de máximo 50 caracteres (sin comillas). SIEMPRE debe ser un título sobre tecnología audiovisual, incluso si el tema parece confuso.
                2. Una breve descripción de una línea apoyando el título.
                3. 5 hashtags relevantes sobre monitores, sonido o AV separados por espacios (incluyendo #Shorts).
                """
                response = self.client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt
                )
                lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
                
                if len(lines) >= 3:
                    short_title = lines[0][:50]
                    if not short_title.endswith("#Shorts"):
                        short_title = (short_title[:42] + " #Shorts").strip()
                    desc = lines[1]
                    hash_tags = lines[2].split()
                    
                    description = (
                        f"{desc}\n\n"
                        f"Mira el vídeo completo aquí: {video_url}\n\n"
                        f"Suscríbete 👉 @GlobalAVInsights"
                    )
                    tags = [t.replace('#', '') for t in hash_tags if t]
                    logger.info(f"Generated dynamic SEO for: {original_title}")
            except Exception as e:
                logger.error(f"Error generating dynamic SEO, using fallback: {e}")

        return {
            "title": short_title,
            "description": description,
            "tags": tags
        }

