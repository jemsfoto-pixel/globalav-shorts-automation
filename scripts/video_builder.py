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

        import random
        # 1. Segment Selection — Random 55s window
        duration = clip.duration
        target_duration = 55
        
        # Ensure we don't start too close to the end
        max_start = max(0, duration - target_duration - 5)
        # Random start time between 5s in and max_start
        start_time = random.uniform(5.0, max_start) if max_start > 5.0 else 0

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

    def build_generative_short(
        self, audio_path: Path, video_paths: list[Path], output_path: Path, script: str
    ) -> Path:
        """Stitch multiple clips together to match audio duration and add voiceover."""
        logger.info(f"Assembling generative short. Audio: {audio_path}")
        
        from moviepy import AudioFileClip
        audio = AudioFileClip(str(audio_path))
        target_duration = audio.duration
        
        clips = []
        for vp in video_paths:
            clips.append(VideoFileClip(str(vp)))
            
        # Stitch clips to match audio duration
        final_video = concatenate_videoclips(clips, method="compose")
        
        # If video is longer than audio, trim it
        if final_video.duration > target_duration:
            final_video = final_video.subclipped(0, target_duration)
        # If video is shorter, loop the last bit or just let it be (ideally Pexels clips are long enough)
        
        # Add audio
        final_video = final_video.with_audio(audio)
        
        # Resize/Crop to 1080x1920
        final_video = final_video.resized(height=self.height)
        if final_video.w > self.width:
            final_video = final_video.cropped(
                x1=(final_video.w - self.width) // 2,
                x2=(final_video.w + self.width) // 2,
            )
            
        # Add Subtitles from script
        # We'll split the script into 2-second chunks for subtitles
        script_words = script.split()
        sub_items = []
        words_per_seg = 4
        for i in range(0, len(script_words), words_per_seg):
            chunk = script_words[i : i + words_per_seg]
            start = (i // words_per_seg) * 2
            if start < target_duration:
                sub_items.append({
                    "text": " ".join(chunk).upper(),
                    "start": start,
                    "end": min(start + 2, target_duration),
                    "highlight": (i // words_per_seg) % 3 == 0
                })
        
        final_video = self.add_subtitles(final_video, sub_items)
        final_video = final_video.with_effects([vfx.FadeOut(1.0)])
        
        logger.info(f"Rendering generative short to {output_path}...")
        final_video.write_videofile(
            str(output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger=None,
        )
        
        final_video.close()
        audio.close()
        for c in clips:
            c.close()
            
        return output_path
