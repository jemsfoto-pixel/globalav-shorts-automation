import asyncio
import edge_tts
from pathlib import Path

async def test_tts():
    voice = "es-ES-AlvaroNeural"
    rate = "+15%"
    text = "¡Hola! Esto es una prueba de la nueva voz dinámica para tus Shorts. ¿Qué te parece el ritmo?"
    output = Path("test_voice.mp3")
    
    print(f"Generating voice with {voice} at {rate} rate...")
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output))
    print(f"✅ Voice generated at {output}")

if __name__ == "__main__":
    asyncio.run(test_tts())
