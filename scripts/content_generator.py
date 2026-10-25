import os
import time
import logging
from pathlib import Path
from typing import Optional, List
from google import genai
from scripts.audio_engine import AudioEngine

logger = logging.getLogger("content_generator")

class ContentGenerator:
    """Generates original video scripts using Gemini and voiceovers using AudioEngine."""

    def __init__(self, config: dict):
        self.config = config
        self.api_key = os.getenv("GOOGLE_API_KEY", "").strip() # User needs to have this in Secrets
        if not self.api_key:
            # Fallback for local testing if env not set, but expected in GitHub Actions
            logger.warning("GOOGLE_API_KEY not found in environment.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-flash-latest"
        self.audio_engine = AudioEngine(config)

    def _generate_with_retry(self, prompt: str, max_retries: int = 4) -> Optional[str]:
        """Call Gemini API with automatic exponential backoff retry on 503/429 errors and model fallback."""
        models_to_try = [self.model_id, "gemini-flash-lite-latest", "gemini-2.5-flash-lite"]
        
        for model in models_to_try:
            delay = 3
            for attempt in range(1, max_retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    err_str = str(e)
                    is_transient = any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand"])
                    if is_transient and attempt < max_retries:
                        logger.warning(f"Gemini {model} temporary error ({err_str}). Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.warning(f"Attempt failed for model {model}: {err_str}")
                        break
                        
        logger.error("All Gemini models and retries failed.")
        return None

    def generate_content(self, topic: str):
        """Generates a script and search keywords for a given topic."""
        logger.info(f"Generating script for topic: {topic}")
        
        prompt = f"""
        Actúa como un creador de YouTube Shorts viral.
        Escribe un guion dinámico y de ritmo rápido en ESPAÑOL sobre: {topic}.
        El guion debe tener exactamente 50-60 palabras para durar unos 45 segundos.
        NO USES emojis, ni formatos complejos (ni asteriscos, ni negritas, ni comillas). Solo texto plano continuo.
        Contexto del canal: Global Audiovisual Insights (tecnología AV, monitores, proyectores, sonido, home theater).
        IMPORTANTE: NO hables de "barras de color", "señales de prueba" o "ajustes técnicos" a menos que el tema lo requiera específicamente. Enfócate en el valor para el espectador.
        REGLAS DE SEO Y RETENCIÓN:
        1. El gancho inicial debe ser muy atractivo y MENCIONAR literalmente en los primeros 3 segundos la palabra clave principal del tema.
        2. El final debe incluir una pregunta interactiva (ej: "¿Tú qué prefieres?", "¿Te ha pasado?") seguida de una rápida petición de suscripción, para fomentar comentarios.
        3. Termina la última frase de manera que conecte fluidamente con el inicio del video (creando un bucle de retención).
        """
        
        try:
            text = self._generate_with_retry(prompt)
            if not text:
                logger.error("Failed to generate script text from Gemini.")
                return None
            script = text.strip().replace("\n", " ").replace("*", "")
            logger.info("Script generated successfully.")
            
            # Extract keywords for Pexels search
            keyword_prompt = f"Read the following Spanish script and extract exactly 3 simple English keywords for stock video search, separated by commas (e.g., monitor, technology, office): {script}"
            kw_text = self._generate_with_retry(keyword_prompt)
            if kw_text:
                keywords = [k.strip() for k in kw_text.split(",") if k.strip()]
            else:
                keywords = ["technology", "screen", "monitor"]
            logger.info(f"Keywords extracted: {keywords}")
            
            return {
                "script": script,
                "keywords": keywords,
                "topic": topic
            }
        except Exception as e:
            logger.error(f"Error generating AI content: {e}")
            return None

    def generate_content_from_video(self, title: str, description: str):
        """Generates a script explaining an existing channel video."""
        logger.info(f"Generating explainer script for video: {title}")
        
        prompt = f"""
        Actúa como un experto ingeniero audiovisual creando un YouTube Short viral y educativo.
        Tu objetivo es ENSEÑAR y EXPLICAR el concepto técnico de este vídeo en ESPAÑOL, de forma clara y directa.
        No hagas un simple resumen o un tráiler del vídeo; el Short debe tener valor educativo por sí mismo.
        
        TÍTULO DEL VÍDEO ORIGEN: {title}
        CONTEXTO TÉCNICO: {description[:800]}
        
        REGLAS ESTRICTAS DE SEO Y RETENCIÓN:
        - Explica 1 o 2 conceptos técnicos clave.
        - Sé conciso pero muy informativo (cero paja).
        - El guion debe tener exactamente 70-85 palabras para durar unos 50-60 segundos.
        - NO USES emojis, ni formatos complejos (ni asteriscos, ni negritas, ni comillas). Solo texto plano continuo.
        - Empieza con un "gancho" inicial educativo muy atractivo que INCLUYA literalmente las palabras clave principales del título.
        - Termina haciendo una pregunta rápida al espectador para generar comentarios (ej: "¿Alguna vez has notado esto en tu TV? Te leo en comentarios") y un rápido "Suscríbete". NO digas "mira el vídeo completo".
        - Opcional: Haz que el final suene como que conecta con la primera frase para crear un bucle visual.
        """
        
        try:
            text = self._generate_with_retry(prompt)
            if not text:
                logger.error("Failed to generate explainer script from Gemini.")
                return None
            script = text.strip().replace("\n", " ").replace("*", "")
            logger.info("Explainer script generated successfully.")
            
            # Extract keywords for Pexels search
            keyword_prompt = f"Read the following Spanish script and extract exactly 3 simple English keywords for stock video search about audiovisual tech, separated by commas (e.g., monitor, technology, audio): {script}"
            kw_text = self._generate_with_retry(keyword_prompt)
            if kw_text:
                keywords = [k.strip() for k in kw_text.split(",") if k.strip()][:3]
            else:
                keywords = ["television", "technology", "screen"]
            logger.info(f"Keywords extracted: {keywords}")
            
            return {
                "script": script,
                "keywords": keywords[:3],
                "topic": title
            }
        except Exception as e:
            logger.error(f"Error generating explainer script: {e}")
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
            text = self._generate_with_retry(prompt)
            if text:
                topics = [line.strip() for line in text.strip().split("\n") if line.strip()]
                logger.info(f"Successfully generated topics: {topics}")
                return topics[:count]
            return []
        except Exception as e:
            logger.error(f"Error generating topics: {e}")
            return []

    def generate_voiceover(self, text: str, output_path: Path) -> Optional[Path]:
        """Convert text to speech using AudioEngine (Edge TTS / gTTS fallback) and save as MP3."""
        logger.info(f"Generating voiceover: {output_path}")
        return self.audio_engine.generate_from_text(text, output_path)
