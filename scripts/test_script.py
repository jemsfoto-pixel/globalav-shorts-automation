import os
import sys
import yaml
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scriptwriter import ScriptWriter

logging.basicConfig(level=logging.INFO)

def run_test():
    with open(PROJECT_ROOT / "config.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    writer = ScriptWriter(config)
    topic = {
        "title": "5 datos increíbles sobre la Inteligencia Artificial",
        "keywords": ["datos curiosos", "IA", "tecnología"]
    }
    
    print("Testing Gemini 2.5 generation...")
    script = writer.generate_script(topic, config["niche"]["topics"]["ia_en_60_segundos"], 50)
    
    if script and "hook" in script:
        print(f"✅ Success! Hook: {script['hook']}")
        print(f"✅ Segments: {len(script['segments'])}")
        for seg in script['segments']:
            print(f"  - {seg['text']} (Vis: {seg['visual_description']})")
    else:
        print("❌ Generation failed or used template fallback.")

if __name__ == "__main__":
    run_test()
