import os
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.assets import AssetFetcher
from scripts.video_builder import VideoBuilder
import yaml

logging.basicConfig(level=logging.INFO)

def run_test():
    with open(PROJECT_ROOT / "config.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    fetcher = AssetFetcher(config)
    output_dir = PROJECT_ROOT / "output" / "test_assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Test Pexels Fetch
    print("--- Fetching Video ---")
    video_path = fetcher._fetch_video("technology", output_dir, 0)
    
    if not video_path:
        print("❌ Failed to fetch video. Pexels API issue or no key.")
        return
        
    print(f"✅ Downloaded video: {video_path}")
    
    # 2. Test VideoBuilder
    print("--- Building Video ---")
    builder = VideoBuilder(config)
    script = {
        "hook": "Prueba de video",
        "segments": [
            {"text": "Esto es texto sobre un video real de pexels", "duration": 4}
        ],
        "cta": "Suscríbete"
    }
    
    assets = [
        {"path": str(video_path), "type": "video"}
    ]
    
    out_vid = PROJECT_ROOT / "output" / "test_render.mp4"
    try:
        builder.build(script, assets, out_vid)
        print(f"✅ Success! Video rendered at: {out_vid}")
    except Exception as e:
        print(f"❌ Render failed: {e}")

if __name__ == "__main__":
    run_test()
