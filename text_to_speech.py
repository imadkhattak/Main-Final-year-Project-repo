import os
import asyncio
import edge_tts
from pydub import AudioSegment
from pydub.playback import play
import tempfile

async def text_to_speech_and_play(text):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name

        # Generate audio using edge-tts
        communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
        await communicate.save(temp_path)

        # Play the audio
        audio = AudioSegment.from_file(temp_path, format="mp3")
        play(audio)

        # Clean up
        os.remove(temp_path)

    except Exception as e:
        print(f"Error in TTS: {e}")
