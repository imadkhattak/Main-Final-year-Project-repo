from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import edge_tts
import tempfile
import os
import asyncio
from transcription_utils import transcribe_audio_to_text
from llama_api import query_llama_api
from database_utils import execute_sql_query, get_database_schema
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import pyaudio
import wave
import webrtcvad
import collections
import logging
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Add this line

# Modify the validate_request function to be more flexible during development
def validate_request(request):
    """Validate that request comes from authorized frontend"""
    if app.debug:  # Allow all requests in debug mode
        return True
    required_header = request.headers.get('X-From-Client')
    if required_header != 'PeshawarMallAssistant':
        logger.warning(f"⚠️ Unauthorized request blocked - missing/invalid header: {required_header}")
        return False
    return True


logging.basicConfig(level=logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logs
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

print("\n🎤 Peshawar Mall Assistant Server Starting")
print("=" * 50)
print("⚠️  VAD will ONLY initialize when frontend requests it")
print("=" * 50)

try:
    db_schema = get_database_schema()
    schema_text = "\n".join([f"{table}: {', '.join(columns)}" for table, columns in db_schema.items()])
    logger.info("✅ Database schema loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load database schema: {e}")
    schema_text = ""

# Global recorder instance - NOT initialized until needed
current_recorder = None
recorder_initialized = False
session_active = False  # Track if conversation session is activ
class ImprovedVADRecorder:
    def __init__(self):
        self.sample_rate = 16000
        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.vad = webrtcvad.Vad(3)  # Most aggressive setting (0-3)
        self.audio = None
        self.is_recording = False
        self.stream = None
        self.speech_frames_threshold = 8  # Increased to reduce false positives
        self.silence_frames_threshold = 35  # Increased silence threshold
        self.min_speech_duration = 0.5  # Minimum speech duration in seconds
        logger.info("🎙️ VAD Recorder initialized (READY but NOT STARTED)")

    def _initialize_audio(self):
        try:
            if self.audio is not None:
                self._cleanup_audio()
            time.sleep(0.1)
            self.audio = pyaudio.PyAudio()
            logger.info(f"🔍 Found {self.audio.get_device_count()} audio devices")
            
            # Find the best input device
            best_device = None
            for i in range(self.audio.get_device_count()):
                device = self.audio.get_device_info_by_index(i)
                if device['maxInputChannels'] > 0:
                    if 'microphone' in device['name'].lower() or 'mic' in device['name'].lower():
                        best_device = i
                        logger.info(f"📱 Selected input device {i}: {device['name']}")
                        break
            
            if best_device is None:
                # Fallback to first available input device
                for i in range(self.audio.get_device_count()):
                    device = self.audio.get_device_info_by_index(i)
                    if device['maxInputChannels'] > 0:
                        best_device = i
                        logger.info(f"📱 Using fallback input device {i}: {device['name']}")
                        break
            
            self.input_device = best_device
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize audio: {e}")
            return False

    def _cleanup_audio(self):
        try:
            if self.stream and not self.stream.is_stopped():
                self.stream.stop_stream()
            if self.stream:
                self.stream.close()
            self.stream = None
            if self.audio:
                self.audio.terminate()
                self.audio = None
        except Exception as e:
            logger.warning(f"⚠️ Error during audio cleanup: {e}")
        time.sleep(0.1)

    def record_with_vad(self, max_duration=15, silence_timeout=4):
        logger.info("🎙️ Starting VAD-based recording session")
        if not self._initialize_audio():
            logger.error("❌ Failed to initialize audio - cannot record")
            return None
            
        try:
            # Create audio stream
            stream_params = {
                'format': pyaudio.paInt16,
                'channels': 1,
                'rate': self.sample_rate,
                'input': True,
                'frames_per_buffer': self.frame_size
            }
            
            if hasattr(self, 'input_device') and self.input_device is not None:
                stream_params['input_device_index'] = self.input_device
            
            self.stream = self.audio.open(**stream_params)
            self.stream.start_stream()
            logger.info("🎤 Audio stream started - waiting for speech...")
            
            frames = []
            ring_buffer = collections.deque(maxlen=10)
            is_speaking = False
            speech_started = False
            recording_start_time = time.time()
            silence_frames = 0
            speech_frames = 0
            self.is_recording = True
            
            while self.is_recording:
                current_time = time.time()
                if current_time - recording_start_time > max_duration:
                    logger.info(f"⏰ Max duration ({max_duration}s) reached")
                    break
                
                try:
                    frame = self.stream.read(self.frame_size, exception_on_overflow=False)
                    is_speech = self.vad.is_speech(frame, self.sample_rate)
                    
                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                    else:
                        silence_frames += 1
                        speech_frames = 0
                    
                    ring_buffer.append((frame, is_speech))

                    # Detect start of speech
                    if not speech_started and speech_frames >= self.speech_frames_threshold:
                        speech_started = True
                        logger.info("🗣️ Speech detected - starting recording")
                        # Add buffered audio to frames
                        frames.extend([f for f, _ in ring_buffer])

                    elif speech_started:
                        frames.append(frame)
                        # Check for end of speech
                        if silence_frames >= self.silence_frames_threshold:
                            logger.info("🔇 End of speech detected")
                            break
                            
                except Exception as e:
                    logger.error(f"❌ Error reading audio frame: {e}")
                    break

            self._cleanup_audio()
            
            if not frames or not speech_started:
                logger.warning("❌ No valid speech recorded")
                return None

            # Check minimum duration
            duration = len(frames) * self.frame_duration_ms / 1000
            if duration < self.min_speech_duration:
                logger.warning(f"❌ Speech too short ({duration:.1f}s < {self.min_speech_duration}s)")
                return None

            # Save recorded audio to file
            filename = os.path.join(tempfile.gettempdir(), f"vad_recording_{int(time.time()*1000)}.wav")
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            logger.info(f"✅ Recorded {duration:.1f}s of audio to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Error in VAD recording: {e}")
            return None
        finally:
            self._cleanup_audio()
            self.is_recording = False

    def stop_recording(self):
        logger.info("🛑 Stopping recording")
        self.is_recording = False

def get_vad_recorder():
    global current_recorder
    # ONLY create recorder when actually needed
    if current_recorder is None:
        logger.info("🎙️ Creating VAD recorder for the first time")
        current_recorder = ImprovedVADRecorder()
    return current_recorder

def process_user_query(transcribed_text):
    logger.info(f"🤔 Processing user query: {transcribed_text}")
    
    try:
        # Generate SQL query
        sql_response = query_llama_api(transcribed_text, schema_text, mode="sql")
        logger.info(f"📊 Generated SQL Response: {sql_response}")
        
        # Extract SQL queries
        sql_queries = [q.strip() for q in re.split(r';|\n', sql_response) 
                      if q.strip().lower().startswith(('select', 'insert', 'update', 'delete'))]
        
        structured_results = []
        for query in sql_queries:
            try:
                query_result = execute_sql_query(query)
                structured_results.append({"query": query, "result": query_result})
            except Exception as e:
                logger.error(f"❌ SQL query error: {e}")
                structured_results.append({"query": query, "result": f"Error: {str(e)}"})

        # Generate final response
        prompt = f"""
You are a helpful assistant at Peshawar Mall. A customer asked: "{transcribed_text}".

The following are results from the database:
{structured_results}

Please respond in a polite, helpful, and conversational tone using the above results.
Keep your response concise and natural for voice interaction.
If any information is missing, say so politely without guessing.
"""
        final_response = query_llama_api(prompt, mode="chat")
        logger.info(f"💬 Final Response: {final_response}")
        return final_response
        
    except Exception as e:
        logger.error(f"❌ Error processing query: {e}")
        return "I apologize, but I'm having trouble processing your request right now. Could you please try again?"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initialize-recorder', methods=['POST'])
def initialize_recorder():
    """Initialize the VAD recorder - ONLY called from authorized frontend"""
    try:
        # Validate request comes from authorized frontend
        if not validate_request(request):
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        global recorder_initialized, session_active
        
        # Mark session as active
        session_active = True
        
        if recorder_initialized:
            logger.info("🎙️ Recorder already initialized")
            return jsonify({"success": True, "message": "Recorder already initialized"})
        
        logger.info("🎙️ Initializing VAD recorder...")
        
        # Initialize the recorder
        recorder = get_vad_recorder()
        
        if recorder:
            recorder_initialized = True
            logger.info("✅ VAD recorder initialized successfully")
            return jsonify({"success": True, "message": "Recorder initialized"})
        else:
            logger.error("❌ Failed to initialize VAD recorder")
            return jsonify({"success": False, "error": "Failed to initialize recorder"}), 500
            
    except Exception as e:
        logger.error(f"❌ Error initializing recorder: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/start-vad-recording', methods=['POST'])
def start_vad_recording():
    """Start VAD recording - ONLY works if session is active and authorized"""
    try:
        # Validate authorization
        if not validate_request(request):
            logger.warning("⚠️ Unauthorized VAD recording attempt blocked")
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        # Check if session is active
        if not session_active:
            logger.warning("⚠️ VAD recording attempted without active session")
            return jsonify({"success": False, "error": "No active session"}), 400
        
        # Check if recorder is initialized
        if not recorder_initialized:
            logger.warning("⚠️ VAD recording attempted without initialized recorder")
            return jsonify({"success": False, "error": "Recorder not initialized"}), 400
        
        logger.info("🎙️ Starting VAD recording session")
        
        data = request.get_json() or {}
        max_duration = data.get('max_duration', 15)
        silence_timeout = data.get('silence_timeout', 4)
        
        recorder = get_vad_recorder()
        
        # Record with VAD
        audio_file = recorder.record_with_vad(max_duration, silence_timeout)
        
        if audio_file and os.path.exists(audio_file):
            # Transcribe the audio
            logger.info("📝 Transcribing recorded audio...")
            transcript = transcribe_audio_to_text(audio_file)
            
            # Clean up audio file
            try:
                os.remove(audio_file)
            except:
                pass
            
            if transcript and transcript.strip():
                logger.info(f"✅ Transcription successful: {transcript}")
                return jsonify({
                    "success": True,
                    "transcript": transcript.strip()
                })
            else:
                logger.warning("❌ Empty transcription")
                return jsonify({
                    "success": False,
                    "error": "No speech detected or transcription failed",
                    "transcript": ""
                })
        else:
            logger.warning("❌ No audio recorded")
            return jsonify({
                "success": False,
                "error": "No audio recorded",
                "transcript": ""
            })
            
    except Exception as e:
        logger.error(f"❌ Error in VAD recording: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stop-recording', methods=['POST'])
def stop_recording():
    """Stop any ongoing recording"""
    try:
        # Validate authorization
        if not validate_request(request):
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        if current_recorder:
            current_recorder.stop_recording()
            logger.info("🛑 Recording stopped")
            return jsonify({"success": True, "message": "Recording stopped"})
        else:
            return jsonify({"success": True, "message": "No active recording"})
            
    except Exception as e:
        logger.error(f"❌ Error stopping recording: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/end-session', methods=['POST'])
def end_session():
    """End the conversation session"""
    try:
        # Validate authorization
        if not validate_request(request):
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        global session_active, recorder_initialized, current_recorder
        
        # Stop any ongoing recording
        if current_recorder:
            current_recorder.stop_recording()
        
        # Reset session state
        session_active = False
        recorder_initialized = False
        current_recorder = None
        
        logger.info("🔚 Session ended - recorder reset")
        return jsonify({"success": True, "message": "Session ended"})
        
    except Exception as e:
        logger.error(f"❌ Error ending session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', 'en-US-AriaNeural')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        logger.info(f"🔊 TTS request: {text[:50]}...")
        
        async def generate_tts():
            communicate = edge_tts.Communicate(text, voice)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()
            
            await communicate.save(temp_file.name)
            return temp_file.name
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_file = loop.run_until_complete(generate_tts())
        finally:
            loop.close()
        
        def cleanup_file():
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except:
                pass
        
        response = send_file(
            audio_file,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='speech.mp3'
        )
        
        # Schedule cleanup after response is sent
        threading.Timer(5.0, cleanup_file).start()
        
        logger.info("✅ TTS audio sent successfully")
        return response
        
    except Exception as e:
        logger.error(f"❌ TTS error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        logger.info(f"💬 Chat request: {user_message}")
        
        # Process the query
        response = process_user_query(user_message)
        
        return jsonify({
            "success": True,
            "response": response
        })
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        return jsonify({
            "success": False,
            "error": "Sorry, I encountered an error processing your request."
        }), 500

if __name__ == '__main__':
    logger.info("🚀 Server ready - NO audio initialization until user interaction")
    logger.info("📝 Ready to receive requests at http://127.0.0.1:5000")
    logger.info("🎯 Click 'Start Conversation' to begin!")
    app.run(debug=True, host='127.0.0.1', port=5000)