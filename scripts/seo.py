import logging

logger = logging.getLogger("seo")

class SEOGenerator:
    """Generates optimized metadata for YouTube Shorts."""

    def __init__(self, config: dict):
        self.config = config

    def generate(self, original_title: str, video_url: str) -> dict:
        """Create title and description based on original video context."""
        
        # Simple Hook + Original Title + #Shorts
        # Limit to 50 chars for the hook part
        hook = "¡Increíble fidelidad! 🔊"
        clean_title = original_title.split('|')[0].strip()
        
        short_title = f"{hook} {clean_title}"[:40] + " #Shorts"
        
        description = (
            f"Mira el video completo aquí: {video_url}\n\n"
            "Suscríbete para más tips de calibración y pruebas de sonido de alta fidelidad. "
            "#GlobalAVInsights #Shorts #HiFi #Audio"
        )
        
        return {
            "title": short_title,
            "description": description,
            "tags": ["Shorts", "GlobalAVInsights", "HiFi", "Audio", "Calibración"]
        }
