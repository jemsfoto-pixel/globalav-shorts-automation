import os
import logging
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

logger = logging.getLogger("thumbnail_generator")

class ThumbnailGenerator:
    """Creates eye-catching thumbnails for Shorts."""

    def __init__(self, config: dict):
        self.config = config
        self.font_path = str(Path(config.get("PROJECT_ROOT", ".")) / "templates" / "fonts" / "Montserrat-Bold.ttf")

    def generate(self, video_path: Path, output_path: Path, text: str = "PURA FIDELIDAD"):
        """Extract a frame, enhance it, and add text."""
        logger.info(f"Generating thumbnail for {video_path}...")
        
        # Use ffmpeg to extract a frame at 50% of the duration
        tmp_frame = output_path.with_suffix(".png")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", "00:00:10", # Pick 10s mark
            "-vframes", "1",
            str(tmp_frame)
        ]
        
        try:
            import subprocess
            subprocess.run(cmd, check=True, capture_output=True)
            
            img = Image.open(tmp_frame)
            
            # Enhance Contrast and Saturation
            converter = ImageEnhance.Color(img)
            img = converter.enhance(1.4) # +40% Saturation
            
            converter = ImageEnhance.Contrast(img)
            img = converter.enhance(1.2) # +20% Contrast
            
            # Add Text
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype(self.font_path, 120)
            except:
                font = ImageFont.load_default()
                
            # Draw text with shadow/outline
            w, h = img.size
            text_pos = (w // 2, 200)
            
            # Simple shadow
            draw.text((text_pos[0]+5, text_pos[1]+5), text, font=font, fill="black", anchor="mt")
            draw.text(text_pos, text, font=font, fill="white", anchor="mt")
            
            img.save(output_path)
            if os.path.exists(tmp_frame): os.remove(tmp_frame)
            
            return output_path
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return None
