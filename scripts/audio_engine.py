"""
Audio Engine Module
Generates TTS voiceovers and mixes with background music.
Uses gTTS for free text-to-speech in Spanish.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("audio_engine")

PROJECT_ROOT = Path(__file__).parent.parent

try:
    import edge_tts
    import asyncio
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed — TTS will fallback to gTTS or be unavailable")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed")

try:
    from moviepy import AudioFileClip, CompositeAudioClip, concatenate_audioclips, AudioArrayClip
    MOVIEPY_AUDIO_AVAILABLE = True
except ImportError:
    MOVIEPY_AUDIO_AVAILABLE = False
    logger.warning("MoviePy audio not available")


class AudioEngine:
    """Generates voiceovers and mixes background music."""

    def __init__(self, config: dict):
        self.config = config
        self.language = (
            config.get("audio", {}).get("language")
            or config.get("channel", {}).get("language")
            or config.get("niche", {}).get("language", "es")
        )
        self.voice = config.get("audio", {}).get("voice", "es-ES-AlvaroNeural")
        self.rate = config.get("audio", {}).get("rate", "+15%") # Default faster for Shorts

    def _synthesize_text_to_file(self, text: str, output_file: Path) -> bool:
        """Helper to synthesize a single piece of text to an MP3 file using Edge TTS (or gTTS fallback)."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        if EDGE_TTS_AVAILABLE:
            try:
                async def _gen():
                    communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
                    await communicate.save(str(output_file))

                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import nest_asyncio
                        nest_asyncio.apply()
                    asyncio.run(_gen())
                except Exception:
                    asyncio.run(_gen())
                return True
            except Exception as e:
                logger.warning(f"edge-tts failed: {e}. Falling back to gTTS if available...")

        if GTTS_AVAILABLE:
            try:
                tts = gTTS(text=text, lang=self.language, slow=False)
                tts.save(str(output_file))
                return True
            except Exception as e:
                logger.error(f"gTTS failed: {e}")
                return False

        logger.error("No TTS engine available to synthesize text.")
        return False

    def generate_from_text(self, text: str, output_path: Path) -> Optional[Path]:
        """Generate voiceover directly from a raw text string."""
        if not text:
            logger.warning("Empty text passed for voiceover generation.")
            return None
        success = self._synthesize_text_to_file(text, output_path)
        if success and output_path.exists():
            logger.info(f"✅ Voiceover created ({'edge-tts' if EDGE_TTS_AVAILABLE else 'gTTS'}): {output_path.name}")
            return output_path
        return None

    def generate_voiceover(self, script: dict, output_dir: Path) -> Optional[Path]:
        """
        Generate a TTS voiceover from the script segments.
        Returns path to the combined voiceover .mp3 file.
        """
        if not EDGE_TTS_AVAILABLE and not GTTS_AVAILABLE:
            logger.warning("No TTS engine available, skipping voiceover")
            return None

        output_dir.mkdir(parents=True, exist_ok=True)

        # Build the full narration text from segments
        parts = []

        # Hook
        hook = script.get("hook", "")
        if hook:
            parts.append(hook)

        # Segments
        for segment in script.get("segments", []):
            text = segment.get("text", "")
            if text:
                parts.append(text)

        # CTA
        cta = script.get("cta", "")
        if cta:
            parts.append(cta)

        if not parts:
            logger.warning("No text segments found for TTS")
            return None

        # Generate individual segment audio files for timing control
        segment_paths = []
        for i, text in enumerate(parts):
            segment_path = output_dir / f"tts_segment_{i:03d}.mp3"
            success = self._synthesize_text_to_file(text, segment_path)
            if success and segment_path.exists():
                segment_paths.append(segment_path)
                logger.info(f"TTS segment {i} ({'edge-tts' if EDGE_TTS_AVAILABLE else 'gTTS'}): {len(text)} chars")
            else:
                logger.error(f"TTS failed for segment {i}")

        if not segment_paths:
            return None

        # Combine all segments into one file
        combined_path = output_dir / "voiceover_full.mp3"
        try:
            if MOVIEPY_AUDIO_AVAILABLE:
                clips = [AudioFileClip(str(p)) for p in segment_paths]
                
                # Add 0.5s silence at the end to ensure it doesn't cut mid-sentence
                silence_duration = 0.5
                import numpy as np
                # Create a small silent clip
                # Note: moviepy 2.x AudioArrayClip
                silence = AudioArrayClip(np.zeros((int(44100 * silence_duration), 2)), fps=44100)
                
                combined = concatenate_audioclips(clips + [silence])
                combined.write_audiofile(str(combined_path), logger=None)
                combined.close()
                for c in clips:
                    c.close()
            else:
                # Fallback: use the first segment
                import shutil
                shutil.copy2(segment_paths[0], combined_path)

            logger.info(f"✅ Voiceover generated: {combined_path.name}")
            return combined_path

        except Exception as e:
            logger.error(f"Failed to combine TTS segments: {e}")
            return segment_paths[0] if segment_paths else None

    def get_segment_durations(self, script: dict, voiceover_path: Path) -> list:
        """
        Calculate the duration each segment should have based on
        the voiceover audio length, distributed proportionally.
        """
        if not MOVIEPY_AUDIO_AVAILABLE or not voiceover_path:
            return []

        try:
            audio = AudioFileClip(str(voiceover_path))
            total_audio_duration = audio.duration
            audio.close()

            # Count segments (hook + segments + cta)
            num_hook = 1 if script.get("hook") else 0
            num_segments = len(script.get("segments", []))
            num_cta = 1 if script.get("cta") else 0
            total_parts = num_hook + num_segments + num_cta

            if total_parts == 0:
                return []

            # Distribute duration proportionally by text length
            parts_text = []
            if script.get("hook"):
                parts_text.append(len(script["hook"]))
            for seg in script.get("segments", []):
                parts_text.append(len(seg.get("text", "")))
            if script.get("cta"):
                parts_text.append(len(script["cta"]))

            total_chars = sum(parts_text) or 1
            durations = [
                max(2.0, (chars / total_chars) * total_audio_duration)
                for chars in parts_text
            ]

            return durations

        except Exception as e:
            logger.error(f"Failed to calculate segment durations: {e}")
            return []

    def mix_with_music(
        self,
        voiceover_path: Path,
        total_duration: float,
        output_path: Path,
        music_volume: float = 0.15,
    ) -> Optional[Path]:
        """
        Mix voiceover with background music.
        Music volume is reduced (ducking) to let the voice be heard clearly.
        """
        if not MOVIEPY_AUDIO_AVAILABLE:
            logger.warning("MoviePy audio not available, returning voiceover only")
            return voiceover_path

        try:
            # Load voiceover
            voice = AudioFileClip(str(voiceover_path))

            # Try to find background music
            music_path = self._find_background_music()

            if music_path:
                music = AudioFileClip(str(music_path))
                # Loop music to match video duration
                if music.duration < total_duration:
                    loops_needed = int(total_duration / music.duration) + 1
                    music_clips = [AudioFileClip(str(music_path)) for _ in range(loops_needed)]
                    music = concatenate_audioclips(music_clips)

                # Trim to video duration and lower volume
                music = music.subclipped(0, total_duration).with_volume_scaled(music_volume)

                # Combine voice + music
                final_audio = CompositeAudioClip([music, voice])
            else:
                logger.info("No background music found, using voiceover only")
                final_audio = voice

            final_audio.write_audiofile(str(output_path), logger=None)

            # Cleanup
            voice.close()
            final_audio.close()

            logger.info(f"✅ Mixed audio: {output_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
            return voiceover_path

    def _find_background_music(self) -> Optional[Path]:
        """Search for background music files in known locations."""
        search_paths = [
            PROJECT_ROOT / "templates" / "background.mp3",
            PROJECT_ROOT / "assets" / "music" / "background.mp3",
        ]

        # Also search for any .mp3 in the music folder
        music_dir = PROJECT_ROOT / "assets" / "music"
        if music_dir.exists():
            for mp3 in music_dir.glob("*.mp3"):
                search_paths.append(mp3)

        for path in search_paths:
            if path.exists():
                logger.info(f"Found background music: {path.name}")
                return path

        return None
