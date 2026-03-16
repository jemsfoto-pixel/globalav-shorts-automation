"""
Trend Research Module
Finds trending topics for the selected niche using keyword analysis.
Falls back to a curated topic bank when APIs are unavailable.
"""

import os
import random
import logging
import requests
from typing import Optional

logger = logging.getLogger("research")

# ============================================================
# Curated Topic Banks (for offline / fallback operation)
# ============================================================
TOPIC_BANK = {
    "ia_en_60_segundos": [
        {"title": "5 herramientas de IA que reemplazan tu trabajo", "keywords": ["IA", "herramientas", "productividad", "trabajo"]},
        {"title": "Qué puede hacer la IA que tú no sabías", "keywords": ["IA", "capacidades", "sorprendente"]},
        {"title": "Cómo usar Gemini gratis para todo", "keywords": ["Gemini", "IA gratis", "Google", "tutorial"]},
        {"title": "IA que crea vídeos en 10 segundos", "keywords": ["IA", "vídeo", "generación", "Sora"]},
        {"title": "3 IAs que nadie conoce y son brutales", "keywords": ["IA", "herramientas", "desconocidas", "productividad"]},
        {"title": "IA detecta mentiras mejor que un humano", "keywords": ["IA", "detección", "mentiras", "tecnología"]},
        {"title": "Así trabaja un programador con IA en 2026", "keywords": ["IA", "programación", "Copilot", "código"]},
        {"title": "Tu móvil ya usa IA sin que lo sepas", "keywords": ["IA", "móvil", "smartphone", "funciones"]},
        {"title": "IA que escribe correos perfectos por ti", "keywords": ["IA", "email", "productividad", "automatización"]},
        {"title": "La IA que predice el futuro del mercado", "keywords": ["IA", "predicción", "mercado", "finanzas"]},
        {"title": "Robot con IA aprende a caminar en 5 minutos", "keywords": ["IA", "robótica", "aprendizaje", "ciencia"]},
        {"title": "IA transforma tu foto en un cuadro famoso", "keywords": ["IA", "arte", "imagen", "estilo"]},
        {"title": "5 webs con IA gratis que no conocías", "keywords": ["IA", "webs", "gratis", "herramientas"]},
        {"title": "IA compone música mejor que muchos humanos", "keywords": ["IA", "música", "composición", "creatividad"]},
        {"title": "Cómo la IA está revolucionando la medicina", "keywords": ["IA", "medicina", "salud", "diagnóstico"]},
        {"title": "IA traduce idiomas en tiempo real", "keywords": ["IA", "traducción", "idiomas", "comunicación"]},
        {"title": "ChatGPT vs Gemini: ¿quién gana en 2026?", "keywords": ["ChatGPT", "Gemini", "comparación", "IA"]},
        {"title": "IA genera imágenes fotorrealistas gratis", "keywords": ["IA", "imágenes", "generación", "gratis"]},
        {"title": "Así se entrena una IA con tus datos", "keywords": ["IA", "entrenamiento", "datos", "machine learning"]},
        {"title": "IA que resume libros enteros en 1 minuto", "keywords": ["IA", "resumen", "libros", "lectura"]},
        # --- Trucos IA ---
        {"title": "Truco oculto de ChatGPT para escribir como tú", "keywords": ["ChatGPT", "truco", "escritura", "personalización"]},
        {"title": "Cómo usar Claude para analizar PDFs gigantes gratis", "keywords": ["Claude", "truco", "PDF", "análisis"]},
        {"title": "3 prompts de Midjourney que parecen fotos reales", "keywords": ["Midjourney", "truco", "prompts", "fotorealismo"]},
        {"title": "Ahorra 10 horas a la semana con este truco de IA", "keywords": ["IA", "truco", "productividad", "tiempo"]},
        {"title": "El truco definitivo para crear presentaciones con IA", "keywords": ["IA", "truco", "presentaciones", "diseño"]},
        # --- Novedades Tech ---
        {"title": "Gemini 2.5: La IA que ya puede razonar como un humano", "keywords": ["Gemini", "novedad", "Google", "razonamiento"]},
        {"title": "Sora ya es público: Cómo crear tus primeros vídeos", "keywords": ["Sora", "novedad", "OpenAI", "vídeo"]},
        {"title": "Apple Intelligence llega a todos los iPhone antiguos", "keywords": ["Apple", "novedad", "iPhone", "IA"]},
        {"title": "NVIDIA presenta el chip más potente de la historia", "keywords": ["NVIDIA", "novedad", "hardware", "chips"]},
        {"title": "La primera ciudad construida por robots e IA en 2026", "keywords": ["IA", "novedad", "robótica", "futuro"]},
    ],
    "curiosidades": [
        {"title": "5 cosas que tu cerebro hace sin que lo sepas", "keywords": ["cerebro", "ciencia", "curiosidades", "mente"]},
        {"title": "El animal más resistente del planeta no es lo que piensas", "keywords": ["animales", "resistencia", "tardígrado", "naturaleza"]},
        {"title": "Por qué no puedes hacerte cosquillas a ti mismo", "keywords": ["cosquillas", "cerebro", "ciencia", "cuerpo"]},
        {"title": "El color que no existe pero tú lo ves", "keywords": ["colores", "percepción", "óptica", "cerebro"]},
        {"title": "5 inventos accidentales que cambiaron el mundo", "keywords": ["inventos", "accidentes", "historia", "cambio"]},
        {"title": "Por qué el tiempo pasa más rápido cuando creces", "keywords": ["tiempo", "percepción", "edad", "psicología"]},
        {"title": "El lugar más silencioso del mundo te vuelve loco", "keywords": ["silencio", "cámara anecoica", "sonido", "récord"]},
        {"title": "Hay más estrellas que granos de arena en la Tierra", "keywords": ["estrellas", "universo", "astronomía", "números"]},
        {"title": "Tu ADN tiene instrucciones para hacer un virus", "keywords": ["ADN", "genética", "virus", "ciencia"]},
        {"title": "Los pulpos tienen 3 corazones y sangre azul", "keywords": ["pulpos", "animales", "biología", "curiosidades"]},
        {"title": "El WiFi fue inventado por una actriz de Hollywood", "keywords": ["WiFi", "invención", "Hedy Lamarr", "tecnología"]},
        {"title": "Puedes vivir sin estómago pero no sin hígado", "keywords": ["cuerpo", "órganos", "medicina", "curiosidades"]},
        {"title": "La miel nunca caduca, se encontró en tumbas egipcias", "keywords": ["miel", "Egipto", "conservación", "alimentos"]},
        {"title": "Los delfines duermen con un ojo abierto", "keywords": ["delfines", "sueño", "cerebro", "animales"]},
        {"title": "Un rayo tiene 5 veces más calor que el sol", "keywords": ["rayo", "temperatura", "sol", "física"]},
    ],
    "finanzas": [
        {"title": "3 errores que te mantienen pobre sin saberlo", "keywords": ["errores", "dinero", "pobreza", "finanzas"]},
        {"title": "Cómo invertir con solo 10 euros", "keywords": ["inversión", "principiantes", "poco dinero", "apps"]},
        {"title": "La regla 50/30/20 que cambiará tu vida", "keywords": ["presupuesto", "ahorro", "regla", "finanzas"]},
        {"title": "5 formas de ganar dinero mientras duermes", "keywords": ["ingresos pasivos", "dinero", "automatización", "inversión"]},
        {"title": "Bitcoin en 2026: ¿invertir o huir?", "keywords": ["Bitcoin", "cripto", "inversión", "2026"]},
        {"title": "Apps gratis que invierten tu dinero por ti", "keywords": ["apps", "inversión", "robo-advisor", "gratis"]},
        {"title": "El hábito de 5 minutos que te hará rico", "keywords": ["hábitos", "riqueza", "finanzas", "productividad"]},
        {"title": "Cómo ahorrar 5000€ en un año sin sufrir", "keywords": ["ahorro", "dinero", "anual", "método"]},
        {"title": "ETFs: la forma más segura de empezar a invertir", "keywords": ["ETFs", "inversión", "seguridad", "bolsa"]},
        {"title": "Warren Buffett nunca haría esto con su dinero", "keywords": ["Buffett", "inversión", "consejos", "errores"]},
        {"title": "Interés compuesto: la 8ª maravilla del mundo", "keywords": ["interés compuesto", "inversión", "matemáticas", "dinero"]},
        {"title": "Por qué los ricos usan deuda para ganar más", "keywords": ["deuda", "apalancamiento", "ricos", "estrategia"]},
    ],
}


class TrendResearcher:
    """Finds trending topics for video production."""

    def __init__(self, config: dict):
        self.config = config
        self.pexels_key = os.getenv("PEXELS_API_KEY", "")

    def get_trending_topic(
        self,
        niche_key: str,
        exclude: Optional[list] = None,
    ) -> dict:
        """
        Get a trending topic for the given niche.
        Tries online research first, falls back to curated bank.
        """
        exclude = exclude or []

        # Try online research first
        online_topic = self._try_online_research(niche_key, exclude)
        if online_topic:
            return online_topic

        # Fallback to curated topic bank
        logger.info("Using curated topic bank (offline mode)")
        return self._pick_from_bank(niche_key, exclude)

    def _try_online_research(self, niche_key: str, exclude: list) -> Optional[dict]:
        """Try to find trending topics online (future: Google Trends API)."""
        # Google Trends doesn't have an official API, so we use the curated bank
        # In the future, this could use pytrends or scraping
        return None

    def _pick_from_bank(self, niche_key: str, exclude: list) -> dict:
        """Pick a random unused topic from the curated bank."""
        bank = TOPIC_BANK.get(niche_key, TOPIC_BANK["ia_en_60_segundos"])
        available = [t for t in bank if t["title"] not in exclude]

        if not available:
            # All topics used, reset and pick any
            logger.warning("All topics exhausted, recycling...")
            available = bank

        topic = random.choice(available)
        logger.info(f"Selected from bank: {topic['title']}")
        return topic
