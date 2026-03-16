"""Test script that writes results directly to a file."""
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.channel_manager import ChannelManager

# Write all output to a results file
results_file = PROJECT_ROOT / "test_results.txt"

with open(results_file, 'w', encoding='utf-8') as out:
    out.write("=== ChannelManager Test ===\n")
    
    try:
        logging.basicConfig(level=logging.INFO)
        manager = ChannelManager(
            "https://www.youtube.com/@GlobalAVInsights",
            history_file=str(PROJECT_ROOT / "output" / "history.json")
        )
        
        out.write("Fetching videos...\n")
        out.flush()
        
        videos = manager.get_eligible_videos(limit=5)
        out.write(f"Found {len(videos)} eligible videos:\n")
        
        for v in videos:
            out.write(f"  - [{v['id']}] {v['title']} ({v['views']} views, {v.get('duration', '?')}s)\n")
        
        out.write("\nSelecting best video...\n")
        best = manager.select_best_video()
        
        if best:
            out.write(f"SELECTED: {best['title']} (ID: {best['id']}, Views: {best['views']})\n")
            out.write("STATUS: SUCCESS\n")
        else:
            out.write("SELECTED: None\n")
            out.write("STATUS: NO VIDEOS FOUND\n")
    except Exception as e:
        out.write(f"ERROR: {e}\n")
        import traceback
        out.write(traceback.format_exc())

print(f"Results written to {results_file}")
