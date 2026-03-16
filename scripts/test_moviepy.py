import os
from moviepy import VideoFileClip, ColorClip, TextClip, CompositeVideoClip
from PIL import Image

def test_render():
    w, h = 1080, 1920
    # Create a red video dummy to test if it shows up under the overlay
    red_clip = ColorClip(size=(w, h), color=(255, 0, 0)).with_duration(2)
    
    # Text
    txt = TextClip(text="Test", font_size=60, color="white", font="Arial", size=(w-120, None)).with_duration(2).with_position("center")
    
    # The overlay exactly as in video_builder
    overlay = ColorClip(size=(w, h), color=(0, 0, 0)).with_duration(2).with_opacity(0.4)
    
    comp = CompositeVideoClip([red_clip, overlay, txt])
    comp.write_videofile("test_moviepy_composite.mp4", fps=30)
    
if __name__ == "__main__":
    test_render()
