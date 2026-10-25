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

    @staticmethod
    def sanitize_tags(raw_tags: list, max_total_chars: int = 400) -> list:
        """
        Sanitize tags according to YouTube rules:
        - No quotes, angle brackets, newlines, or internal commas
        - Strip leading '#'
        - Limit tag length to 80 chars
        - YouTube wraps tags containing spaces in quotes, adding 2 chars to total budget
        - Total serialized budget capped at max_total_chars (<= 400, well below 500 limit)
        - Ensure mandatory channel tags are prioritized
        """
        obligatorios = ["GlobalAVInsights", "Global AV Insights", "Shorts", "Audiovisual"]
        all_candidates = list(obligatorios)
        for t in raw_tags:
            if t not in all_candidates:
                all_candidates.append(t)

        cleaned = []
        seen = set()
        total_len = 0

        for item in all_candidates:
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

    def generate(self, original_title: str, video_url: str) -> dict:
        """Create title and description based on original video context."""
        
        short_title = f"¡Descubre esto! 🔊 {original_title[:30]} #Shorts"
        description = (
            f"Mira el video completo aquí: {video_url}\n\n"
            "Suscríbete para más tips de calibración y pruebas de sonido de alta fidelidad. "
            "#GlobalAVInsights #Shorts #HiFi #Audio"
        )
        tags = self.sanitize_tags(["Shorts", "GlobalAVInsights", "HiFi", "Audio", "Tecnología"], max_total_chars=400)
        
        if self.client:
            try:
                prompt = f"""
                Genera metadatos SEO virales para un YouTube Short en español sobre este tema:
                TEMA: {original_title}
                
                Devuelve EXACTAMENTE TRES LÍNEAS de texto plano y NADA MÁS:
                Línea 1: Un título muy gancho y viral de máximo 70 caracteres (sin comillas). Usa fórmulas de alto CTR (ej. "El secreto de...", "Por qué tu...").
                Línea 2: Un párrafo corto (en UNA SOLA LÍNEA, sin saltos de línea internos) rico en palabras clave SEO sobre el tema, generando curiosidad.
                Línea 3: Una lista de 15 a 20 etiquetas (tags) relevantes separadas por comas (sin comillas, sin caracteres extraños). DEBEN incluir "GlobalAVInsights", "Global AV Insights" y "#Shorts".
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
                    raw_tags = [t.strip() for t in lines[2].split(',') if t.strip()]
                    
                    # Extraer los que tienen hashtag para la descripción visual
                    desc_hashtags = " ".join([t for t in raw_tags if t.startswith('#')])
                    if not desc_hashtags:
                        desc_hashtags = "#Shorts #GlobalAVInsights #HiFi #Audio"
                    
                    description = (
                        f"{desc}\n\n"
                        f"{desc_hashtags}\n\n"
                        f"Mira el vídeo completo aquí: {video_url}\n\n"
                        f"¿Qué opinas? ¡Déjalo en los comentarios! 👇\n"
                        f"Suscríbete 👉 @GlobalAVInsights"
                    )
                    
                    # Sanitizar y validar tags garantizando límite seguro (< 400 caracteres)
                    tags = self.sanitize_tags(raw_tags, max_total_chars=400)
                    
                    # Calcular longitud real serializada para el log
                    serialized_len = sum(len(t) + (2 if ' ' in t else 0) for t in tags) + max(0, len(tags) - 1)
                    logger.info(f"Generated dynamic SEO for: {original_title}. Tags count: {len(tags)}, serialized length: {serialized_len}/400 (YouTube limit: 500)")
            except Exception as e:
                logger.error(f"Error generating dynamic SEO, using fallback: {e}")
                tags = self.sanitize_tags(tags, max_total_chars=400)

        return {
            "title": short_title,
            "description": description,
            "tags": tags
        }

