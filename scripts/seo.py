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
                
                Devuelve EXACTAMENTE TRES LÍNEAS de texto plano y NADA MÁS:
                Línea 1: Un título muy gancho y viral de máximo 70 caracteres (sin comillas). Usa fórmulas de alto CTR (ej. "El secreto de...", "Por qué tu...").
                Línea 2: Un párrafo corto (en UNA SOLA LÍNEA, sin saltos de línea internos) rico en palabras clave SEO sobre el tema, generando curiosidad.
                Línea 3: Una lista masiva de 25 a 30 etiquetas (tags) relevantes separadas por comas (buscamos rozar los 500 caracteres). DEBEN incluir "GlobalAVInsights" y "Global AV Insights". Incluye también #Shorts y al menos 3 con hashtag al principio, el resto sin hashtag.
                """
                response = self.client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt
                )
                lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
                
                if len(lines) >= 3:
                    short_title = lines[0][:70]
                    if not short_title.endswith("#Shorts"):
                        short_title = (short_title[:60] + " #Shorts").strip()
                    
                    desc = lines[1]
                    raw_tags = lines[2].split(',')
                    
                    # Extraer los que tienen hashtag para la descripción visual
                    desc_hashtags = " ".join([t.strip() for t in raw_tags if t.strip().startswith('#')])
                    if not desc_hashtags:
                        desc_hashtags = "#Shorts #GlobalAVInsights #HiFi #Audio"
                    
                    description = (
                        f"{desc}\n\n"
                        f"{desc_hashtags}\n\n"
                        f"Mira el vídeo completo aquí: {video_url}\n\n"
                        f"¿Qué opinas? ¡Déjalo en los comentarios! 👇\n"
                        f"Suscríbete 👉 @GlobalAVInsights"
                    )
                    
                    # Limpiar tags para el backend de YouTube (sin #) y asegurar los obligatorios
                    tags = [t.replace('#', '').strip() for t in raw_tags if t.strip()]
                    obligatorios = ["GlobalAVInsights", "Global AV Insights", "Shorts", "Audiovisual"]
                    for tag in obligatorios:
                        # Buscar si ya está ignorando mayúsculas/minúsculas
                        if not any(tag.lower() == t.lower() for t in tags):
                            tags.append(tag)
                    
                    # YouTube permite máximo 500 caracteres en tags. Asegurarnos de no pasarnos.
                    final_tags = []
                    current_len = 0
                    for t in tags:
                        # +1 por la coma que asume YouTube
                        if current_len + len(t) + 1 <= 500:
                            final_tags.append(t)
                            current_len += len(t) + 1
                        else:
                            break
                            
                    tags = final_tags
                    
                    logger.info(f"Generated dynamic SEO for: {original_title}. Tags length: {current_len}/500")
            except Exception as e:
                logger.error(f"Error generating dynamic SEO, using fallback: {e}")

        return {
            "title": short_title,
            "description": description,
            "tags": tags
        }

