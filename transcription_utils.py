from faster_whisper import WhisperModel

class SpeechToText:
    def __init__(self):
        # You can use 'float32' or 'int8' depending on CPU performance
        self.model = WhisperModel("base", device="cpu", compute_type="float32")

    def transcribe(self, audio_file_path):
        print(f"🎧 Transcribing audio: {audio_file_path}")
        try:
            # Force language to English and use beam search for better results
            segments, info = self.model.transcribe(
                audio_file_path,
                language="en",          # <-- Force English
                beam_size=5
            )
            print(f"🌐 Detected Language: {info.language}, Probability: {info.language_probability:.2f}")

            transcript = ""
            for segment in segments:
                print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
                transcript += segment.text.strip() + " "

            transcript = transcript.strip()
            return transcript

        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            return ""

# ✅ Simple function wrapper
def transcribe_audio_to_text(audio_file_path):
    recognizer = SpeechToText()
    return recognizer.transcribe(audio_file_path)
