import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from scripts.assets import AssetFetcher

def test():
    config_path = PROJECT_ROOT / "config.yml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    fetcher = AssetFetcher(config)
    output_dir = PROJECT_ROOT / "output" / "test_videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Test 1: Fetching video for 'inteligencia artificial'")
    video_path = fetcher._fetch_video("inteligencia artificial", output_dir, index=1)
    if video_path:
        print(f"✅ Success: {video_path}")
    else:
        print("❌ Failed to fetch video.")

    print("\nTest 2: Fetching image for 'tecnologia'")
    image_path = fetcher._fetch_image("tecnologia", output_dir, index=2)
    if image_path:
        print(f"✅ Success: {image_path}")
    else:
        print("❌ Failed to fetch image.")

if __name__ == "__main__":
    test()
