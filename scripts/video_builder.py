import os
import logging
from pathlib import Path
from typing import Optional
from moviepy import (
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips,
    vfx,
)

logger = logging.getLogger("video_builder")


class VideoBuilder:
    """Specialized Video Builder for @GlobalAVInsights Shorts."""

    def __init__(self, config: dict):
        self.config = config
        self.width = 1080
        self.height = 1920
        self.fps = 30
        self.font_path = str(
            Path(config.get("PROJECT_ROOT", ".")) / "templates" / "fonts" / "Montserrat-Bold.ttf"
        )
        if not os.path.exists(self.font_path):
            self.font_path = "Arial-Bold"  # Fallback

    def build_short(
        self, input_video: Path, output_path: Path, keywords: Optional[list] = None
    ) -> Path:
        """Process a long video into a 9:16 Short (50-59 seconds)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Processing video: {input_video}")

        clip = VideoFileClip(str(input_video))

        # 1. Segment Selection — 55s starting at ~10% of the video
        duration = clip.duration
        target_duration = 55
        start_time = max(0, min(duration * 0.1, duration - target_duration - 5))

        end_time = min(start_time + target_duration, duration)
        subclip = clip.subclipped(start_time, end_time)
        logger.info(f"  Segment: {start_time:.1f}s → {end_time:.1f}s ({end_time - start_time:.1f}s)")

        # 2. Vertical Cropping (9:16)
        ideal_width = int(subclip.h * 9 / 16)

        if subclip.w > ideal_width:
            x_center = subclip.w // 2
            x1 = x_center - ideal_width // 2
            subclip = subclip.cropped(x1=x1, y1=0, x2=x1 + ideal_width, y2=subclip.h)

        # Resize to final 1080x1920
        subclip = subclip.resized(height=self.height)
        if subclip.w > self.width:
            subclip = subclip.cropped(
                x1=(subclip.w - self.width) // 2,
                x2=(subclip.w + self.width) // 2,
            )

        # 3. Subtitles (from video title words)
        if not keywords:
            title_words = input_video.stem.replace("_", " ").replace("-", " ").split()
            subtitle_items = []
            words_per_seg = 3
            for i in range(0, len(title_words), words_per_seg):
                chunk = title_words[i : i + words_per_seg]
                segment_text = " ".join(chunk).upper()
                seg_idx = i // words_per_seg
                start = seg_idx * 2
                end = start + 2
                if start < target_duration:
                    subtitle_items.append(
                        {
                            "text": segment_text,
                            "start": start,
                            "end": min(end, target_duration),
                            "highlight": seg_idx % 3 == 0,
                        }
                    )
            if subtitle_items:
                subclip = self.add_subtitles(subclip, subtitle_items)

        # 4. Fade Out (1 second) to avoid abrupt ending
        subclip = subclip.with_effects([vfx.FadeOut(1.0)])

        # 5. Render
        logger.info(f"Rendering Short to {output_path}...")
        subclip.write_videofile(
            str(output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger=None,
        )

        subclip.close()
        clip.close()

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Short rendered: {output_path.name} ({size_mb:.1f} MB)")
        return output_path

    def add_subtitles(self, clip, subtitle_data: list):
        """Overlay styled subtitles onto the clip.
        subtitle_data: list of dicts {'text', 'start', 'end', 'highlight'}
        """
        text_clips = []
        for item in subtitle_data:
            color = "#FFD700" if item.get("highlight") else "#FFFFFF"
            try:
                txt = (
                    TextClip(
                        text=item["text"],
                        font_size=80,
                        color=color,
                        font=self.font_path,
                        stroke_color="#000000",
                        stroke_width=3,
                        text_align="center",
                        size=(self.width - 200, None),
                    )
                    .with_duration(item["end"] - item["start"])
                    .with_start(item["start"])
                    .with_position(("center", 1400))
                )
                text_clips.append(txt)
            except Exception as e:
                logger.warning(f"Subtitle failed for '{item['text']}': {e}")

        if text_clips:
            return CompositeVideoClip([clip] + text_clips)
        return clip
