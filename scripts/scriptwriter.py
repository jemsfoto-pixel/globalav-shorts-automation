"""
Script Writer Module
Uses Google Gemini AI (free tier) to generate video scripts.
Falls back to template-based generation when API is unavailable.
"""

import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger("scriptwriter")

# Try to import Gemini
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai not installed, using template fallback")


SCRIPT_PROMPT = """Eres un guionista experto en YouTube Shorts virales en español.

TAREA: Escribe un guion de {duration} segundos sobre: "{topic}"

FORMATO DE SALIDA (JSON estricto):
{{
  "hook": "Frase inicial impactante de 2-3 segundos para captar atención",
  "segments": [
    {{
      "text": "Texto del narrador para este segmento (1-2 frases cortas)",
      "duration": 5,
      "visual_description": "Descripción breve de la imagen/visual que acompaña"
    }}
  ],
  "cta": "Llamada a la acción final (ej: Sígueme para más)"
}}

REGLAS:
1. El HOOK debe ser una pregunta impactante o un dato sorprendente.
2. Si es un TRUCO: Explica los pasos de forma ultra-clara (Paso 1, Paso 2...).
3. Si es una NOVEDAD: Empieza con "¡URGENTE!" o "ACABA DE SALIR" para crear hype.
4. Cada segmento dura 4-7 segundos.
5. Usa frases CORTAS y directas (máx 15 palabras por frase).
6. Total de segmentos: 6-10.
7. Tono: Informal, energético, como hablando a un amigo.
8. El CTA debe invitar a seguir el canal para no perderse más trucos.
9. Palabras clave del nicho a incluir: {keywords}.
10. SOLO devuelve el JSON, sin explicaciones. En español.
"""


class ScriptWriter:
    """Generates video scripts using Gemini AI or templates."""

    def __init__(self, config: dict):
        self.config = config
        self.client = None

        if GEMINI_AVAILABLE:
            api_key = os.getenv(config["apis"]["gemini"]["env_var"], "")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                logger.info("Gemini AI client initialized")

    def generate_script(self, topic: dict, niche: dict, duration: int = 50) -> dict:
        """Generate a video script for the given topic."""
        if self.client:
            script = self._generate_with_gemini(topic, niche, duration)
            if script:
                return script

        logger.info("Using template-based script generation")
        return self._generate_from_template(topic, niche, duration)

    def _generate_with_gemini(self, topic: dict, niche: dict, duration: int) -> Optional[dict]:
        """Generate script using Gemini API."""
        try:
            model = self.config["apis"]["gemini"]["model"]
            prompt = SCRIPT_PROMPT.format(
                duration=duration,
                topic=topic["title"],
                keywords=", ".join(topic.get("keywords", [])),
            )

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
            )

            # Extract JSON from response
            text = response.text.strip()
            # Remove markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            script = json.loads(text)

            # Validate structure
            if "hook" in script and "segments" in script:
                logger.info(f"Gemini generated script with {len(script['segments'])} segments")
                return script
            else:
                logger.warning("Gemini response missing required fields")
                return None

        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None

    def _generate_from_template(self, topic: dict, niche: dict, duration: int) -> dict:
        """Generate a script from templates (fallback when no API)."""
        title = topic["title"]
        keywords = topic.get("keywords", [])

        # Build segments from the topic
        segments = [
            {
                "text": f"¿Sabías esto sobre {keywords[0] if keywords else 'este tema'}?",
                "duration": 5,
                "visual_description": f"Imagen impactante relacionada con {keywords[0] if keywords else title}",
            },
            {
                "text": f"Hoy te cuento sobre: {title}",
                "duration": 5,
                "visual_description": "Texto animado con el título del vídeo",
            },
            {
                "text": "Esto es algo que la mayoría de personas no sabe.",
                "duration": 5,
                "visual_description": "Imagen de persona sorprendida o signo de interrogación",
            },
            {
                "text": f"Y tiene que ver con {keywords[1] if len(keywords) > 1 else 'algo increíble'}.",
                "duration": 5,
                "visual_description": f"Imagen de {keywords[1] if len(keywords) > 1 else 'tecnología'}",
            },
            {
                "text": "Los expertos llevan años estudiando esto.",
                "duration": 5,
                "visual_description": "Imagen de investigadores o laboratorio",
            },
            {
                "text": f"La clave está en {keywords[2] if len(keywords) > 2 else 'la innovación'}.",
                "duration": 5,
                "visual_description": f"Imagen abstracta de {keywords[2] if len(keywords) > 2 else 'innovación'}",
            },
            {
                "text": "Y esto apenas es el principio de lo que viene.",
                "duration": 5,
                "visual_description": "Imagen futurista o de tecnología avanzada",
            },
            {
                "text": f"Lo más sorprendente es que {keywords[3] if len(keywords) > 3 else 'cada vez va más rápido'}.",
                "duration": 5,
                "visual_description": "Gráfico ascendente o imagen de velocidad",
            },
            {
                "text": "¿Tú qué opinas? Déjamelo en los comentarios.",
                "duration": 5,
                "visual_description": "Imagen de comunidad o conversación",
            },
        ]

        # Trim to fit duration
        total = 0
        used_segments = []
        for seg in segments:
            if total + seg["duration"] <= duration - 5:  # Leave room for CTA
                used_segments.append(seg)
                total += seg["duration"]

        return {
            "hook": f"¿Te has preguntado alguna vez sobre {title.lower()}? 🤯",
            "segments": used_segments,
            "cta": "¡Sígueme para más contenido como este! 🔥",
        }
