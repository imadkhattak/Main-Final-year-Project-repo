import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import webrtcvad
import time


class SpeechRecognizer:
    def __init__(self, samplerate=16000):
        self.samplerate = samplerate
        self.vad = webrtcvad.Vad(1)  # Aggressiveness mode (0-3)
        self.frame_duration = 30  # ms
        self.frame_samples = int(samplerate * self.frame_duration / 1000)
        self.silence_frames_threshold = 10  # 300ms of silence to stop



    def record_audio(self, silence_threshold=0.005, silence_duration=2.0, min_record_duration=2.0):
        print("Recording... Speak now.")
        audio_frames = []
        start_time = time.time()
        silence_start = None

        try:
            with sd.InputStream(samplerate=self.samplerate, channels=1, dtype='float32') as stream:
                while True:
                    frame = stream.read(self.frame_samples)[0]
                    audio_frames.append(frame)

                    rms = np.sqrt(np.mean(frame**2))

                    current_time = time.time()
                    duration = current_time - start_time

                    if rms < silence_threshold:
                        if silence_start is None:
                            silence_start = current_time
                        elif current_time - silence_start > silence_duration and duration > min_record_duration:
                            break
                    else:
                        silence_start = None  # Reset if voice detected

            print("Recording complete.")
            return np.concatenate(audio_frames) if audio_frames else None

        except Exception as e:
            print(f"Error while recording: {e}")
            return None



    def save_temp_wav(self, audio_data):
        if audio_data is None:
            return None
            
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            wav.write(tmpfile.name, self.samplerate, (audio_data * 32767).astype(np.int16))
            return tmpfile.name