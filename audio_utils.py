import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import time

def record_audio():
    recognizer = sr.Recognizer()
    
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1  # Wait longer after user stops speaking
    recognizer.phrase_threshold = 0.1
    recognizer.non_speaking_duration = 1.2  # Be less aggressive with silence detection
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Please speak now... ")
        
        try:
            audio = recognizer.listen(source, timeout=30, phrase_time_limit=None)
            print("Recording complete.")
            
            with open("live_audio.wav", "wb") as f:
                f.write(audio.get_wav_data())
            return "live_audio.wav"
            
        except sr.WaitTimeoutError:
            print("No speech detected within timeout period.")
            return None
        except Exception as e:
            print(f"Error capturing audio: {e}")
            return None


def record_audio_advanced():
    """
    Alternative implementation with more sophisticated speech detection
    """
    recognizer = sr.Recognizer()
    
    # More sensitive settings for continuous listening
    recognizer.energy_threshold = 200
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 2.0  # Wait 2 seconds of silence before stopping
    recognizer.phrase_threshold = 0.2
    recognizer.non_speaking_duration = 1.0
    
    with sr.Microphone() as source:
        print("Calibrating microphone for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        
        try:
            # Record with no phrase time limit - will stop when pause_threshold is reached
            audio = recognizer.listen(source, timeout=60, phrase_time_limit=None)
            print("Speech detected and recorded successfully!")
            
            # Save the recorded audio
            audio_data = audio.get_wav_data()
            filename = "live_audio.wav"
            with open(filename, "wb") as f:
                f.write(audio_data)
            
            return filename
            
        except sr.WaitTimeoutError:
            print("Timeout: No speech detected for too long.")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from speech recognition service: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during recording: {e}")
            return None
        


def play_audio(file_path):
    """Play audio file"""
    try:
        audio = AudioSegment.from_file(file_path, format="mp3")
        play(audio)
    except Exception as e:
        print(f"Error playing audio: {e}")


def test_microphone():
    """Test microphone functionality"""
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("Testing microphone...")
        recognizer.adjust_for_ambient_noise(source)
        print("Say something to test the microphone:")
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            print("Microphone test successful!")
            return True
        except Exception as e:
            print(f"Microphone test failed: {e}")
            return False