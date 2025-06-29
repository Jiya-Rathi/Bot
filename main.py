import os
import time
import torch
import torchaudio
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
from transformers import pipeline
import librosa
import numpy as np

from router_factory import get_intent_router
from utils.business_profile import load_profile, save_profile, needs_profile_info, get_next_missing_field, set_profile_field
from flask import Flask, request
from financial_bot import FinancialBot
from invoice_reminder.handler import invoice_routes
from invoice_reminder.whatsapp import send_whatsapp_prompt
from utils.file_manager import get_file_manager
from utils.csv_validator import validate_csv
from utils.column_mapper import map_columns
from ledger.ledger_manager import LedgerManager
from config.settings import (
    TWILIO_ACCOUNT_SID, 
    TWILIO_AUTH_TOKEN,
    GRANITE_API_KEY,
    GRANITE_ENDPOINT
)
from twilio.twiml.messaging_response import MessagingResponse
from message_router import route_user_message

app = Flask(__name__)
bot = FinancialBot()
file_manager = get_file_manager()
intent_router = get_intent_router(bot, use_llm=True)
file_manager = get_file_manager()
LEDGER_PATH = Path("ledger/ledger.json")

# Create temp directory for voice files
TEMP_VOICE_DIR = Path("temp_voice")
TEMP_VOICE_DIR.mkdir(exist_ok=True)

twilio_auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def download_voice_file(media_url: str, user_id: str, auth_tuple: tuple) -> Path:
    """
    Download voice file from WhatsApp media URL
    """
    print("Auth Tuple:",auth_tuple)
    try:
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        # Clean user_id for filename (remove special characters)
        clean_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-")
        
        # Get file extension from URL or default to .ogg for WhatsApp
        file_ext = os.path.splitext(media_url.split('?')[0])[1] or '.ogg'
        filename = TEMP_VOICE_DIR / f'{clean_user_id}_{timestamp}{file_ext}'
        
        print(f"Downloading voice file to: {filename}")
        
        # Download file with authentication
        response = requests.get(media_url, auth=auth_tuple, timeout=30, allow_redirects=True)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Save the downloaded content
        filename.write_bytes(response.content)
        
        print(f"Voice file downloaded successfully: {filename.stat().st_size} bytes")
        return filename
        
    except requests.exceptions.RequestException as e:
        print(f"Voice file download network error: {e}")
        return None
    except Exception as e:
        print(f"Voice file download error: {e}")
        return None

def load_and_preprocess_audio(file_path):
    """
    Load and preprocess audio file using librosa (handles OGG and most formats)
    
    Args:
        file_path (str or Path): Path to audio file
    
    Returns:
        numpy array: Preprocessed audio array at 16kHz, mono
    """
    try:
        file_path = Path(file_path)
        print(f"Loading audio file: {file_path}")
        
        # Check if file exists and has content
        if not file_path.exists():
            print(f"Audio file does not exist: {file_path}")
            return None
            
        file_size = file_path.stat().st_size
        if file_size == 0:
            print(f"Audio file is empty: {file_path}")
            return None
            
        print(f"File size: {file_size} bytes")
        
        # Method 1: Try librosa (handles OGG, MP3, WAV, etc.)
        try:
            print("Attempting to load with librosa...")
            waveform, sample_rate = librosa.load(
                str(file_path), 
                sr=16000,  # Resample to 16kHz
                mono=True,  # Convert to mono
                dtype=np.float32
            )
            
            print(f"Librosa successful: shape={waveform.shape}, sr={sample_rate}")
            
            # Validate audio data
            if len(waveform) == 0:
                print("Loaded audio is empty")
                return None
                
            # Check for very short audio (less than 0.1 seconds)
            if len(waveform) < 0.1 * 16000:
                print(f"Audio too short: {len(waveform)/16000:.2f} seconds")
                return None
                
            return waveform
            
        except Exception as librosa_error:
            print(f"Librosa loading failed: {librosa_error}")
            
            # Method 2: Fallback to torchaudio (for WAV files mainly)
            try:
                print("Falling back to torchaudio...")
                waveform, original_sample_rate = torchaudio.load(str(file_path))
                
                # Convert to mono if stereo
                if waveform.shape[0] > 1:
                    waveform = torch.mean(waveform, dim=0, keepdim=True)
                
                # Resample to 16kHz if needed
                if original_sample_rate != 16000:
                    print(f"Resampling from {original_sample_rate} to 16000 Hz")
                    resampler = torchaudio.transforms.Resample(
                        orig_freq=original_sample_rate, 
                        new_freq=16000
                    )
                    waveform = resampler(waveform)
                
                audio_array = waveform.squeeze().numpy()
                print(f"Torchaudio successful: shape={audio_array.shape}")
                return audio_array
                
            except Exception as torchaudio_error:
                print(f"Torchaudio fallback failed: {torchaudio_error}")
                return None
    
    except Exception as e:
        print(f"Audio loading error: {e}")
        import traceback
        traceback.print_exc()
        return None

def transcribe_audio_medium(file_path):
    """
    Transcribe audio using Whisper small model
    
    Args:
        file_path (str): Path to audio file
    
    Returns:
        str: Transcribed text
    """
    try:
        print(f"Starting transcription for: {file_path}")
        
        # Load and preprocess audio
        audio = load_and_preprocess_audio(file_path)
        if audio is None:
            return "Failed to load audio"
        
        print(f"Audio loaded for transcription: {len(audio)} samples, {len(audio)/16000:.2f} seconds")
        
        # Check for very short audio
        if len(audio) < 0.3 * 16000:  # Less than 0.3 seconds
            return "Audio too short for transcription"
        
        # Determine device
        device = 0 if torch.cuda.is_available() else -1
        torch_dtype = torch.float16 if device >= 0 else torch.float32
        print(f"Using device: {'GPU' if device >= 0 else 'CPU'} with dtype: {torch_dtype}")
        
        # Initialize Whisper pipeline
        try:
            pipe = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-small",
                device=device,
                torch_dtype=torch_dtype,
                return_timestamps=False  # Don't need timestamps for this use case
            )
            
            # Prepare input for the pipeline
            inputs = {
                "array": audio, 
                "sampling_rate": 16000
            }
            
            print("Running transcription...")
            result = pipe(inputs)
            
            # Extract transcription text
            transcription = result.get('text', '').strip()
            print(f"Transcription result: '{transcription}'")
            
            # Return meaningful response
            if not transcription:
                return "No speech detected in audio"
            
            return transcription
            
        except Exception as pipeline_error:
            print(f"Pipeline error: {pipeline_error}")
            # Try with smaller model as fallback
            return transcribe_audio_light(file_path)
    
    except Exception as e:
        print(f"Transcription error: {e}")
        import traceback
        traceback.print_exc()
        return "Transcription failed"

def transcribe_audio_light(file_path):
    """
    Faster transcription using Whisper tiny model (fallback)
    
    Args:
        file_path (str): Path to audio file
    
    Returns:
        str: Transcribed text
    """
    try:
        print("Using light transcription (Whisper tiny)...")
        
        audio = load_and_preprocess_audio(file_path)
        if audio is None:
            return "Failed to load audio"
        
        if len(audio) < 0.3 * 16000:
            return "Audio too short for transcription"
        
        device = 0 if torch.cuda.is_available() else -1
        torch_dtype = torch.float16 if device >= 0 else torch.float32
        
        pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-tiny",  # Much smaller and faster
            device=device,
            torch_dtype=torch_dtype,
            return_timestamps=False
        )
        
        inputs = {"array": audio, "sampling_rate": 16000}
        result = pipe(inputs)
        
        transcription = result.get('text', '').strip()
        print(f"Light transcription result: '{transcription}'")
        
        return transcription if transcription else "No speech detected"
    
    except Exception as e:
        print(f"Light transcription error: {e}")
        return "Transcription failed"

def cleanup_temp_file(file_path: Path):
    """
    Safely clean up temporary files
    """
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            print(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        print(f"Failed to cleanup temp file {file_path}: {e}")

def is_ledger_uploaded() -> bool:
    return LEDGER_PATH.exists() and LEDGER_PATH.stat().st_size > 0

app.register_blueprint(invoice_routes, url_prefix="/invoice")

@app.route("/twilio", methods=["POST"])
def whatsapp_handler():
    temp_files_to_cleanup = []
    
    try:
        user_input = request.form.get("Body", "").strip()
        user_id = request.form.get("From")
        media_url = request.form.get("MediaUrl0")
        media_type = request.form.get("MediaContentType0")
        
        print(f"Received message from {user_id}")
        print(f"Media URL: {media_url}")
        print(f"Media Type: {media_type}")
        print(f"Text input: '{user_input}'")

        # Voice message handling
        if media_url and media_type and media_type.startswith('audio/'):
            print("Processing voice message...")
            try:
                # Download voice file
                voice_file = download_voice_file(media_url, user_id, twilio_auth)
                
                if voice_file and voice_file.exists():
                    temp_files_to_cleanup.append(voice_file)
                    
                    # Transcribe audio
                    print("Starting transcription...")
                    transcription = transcribe_audio_medium(str(voice_file))
                    print(f"Transcription complete: '{transcription}'")
                    
                    # Check if transcription was successful
                    if transcription and not transcription.startswith(("Transcription failed", "Failed to load", "Audio too short")):
                        # Use transcription as user input
                        user_input = transcription
                        print(f"Using transcription as input: '{user_input}'")
                    else:
                        # Handle transcription failure
                        error_msg = transcription if transcription else "Could not process voice message"
                        response = f"🎙 Sorry, I couldn't understand the voice message: {error_msg}\n\nPlease try again or send a text message."
                        twiml = MessagingResponse()
                        twiml.message(response)
                        return str(twiml)
                        
                else:
                    response = "🎙 Sorry, I couldn't download the voice message. Please try again or send text."
                    twiml = MessagingResponse()
                    twiml.message(response)
                    return str(twiml)

            except Exception as voice_error:
                print(f"Voice processing failed: {voice_error}")
                import traceback
                traceback.print_exc()
                response = "🎙 Sorry, there was an error processing your voice message. Please try sending text instead."
                twiml = MessagingResponse()
                twiml.message(response)
                return str(twiml)
        if media_url:
            # 1. Handle CSV Upload (Ledger)
            if media_type == "text/csv":
                response = handle_csv_upload(media_url, user_id)
                twiml = MessagingResponse()
                twiml.message(response)
                return str(twiml)

            # 2. Handle Invoice Image Upload
            if "image" in media_type or media_type == "application/pdf":
                from invoice_reminder.handler import upload_invoice_from_url
                response = upload_invoice_from_url(media_url, user_id)
                twiml = MessagingResponse()
                twiml.message(response)
                return str(twiml)
        # Check if ledger is uploaded
        if not is_ledger_uploaded():
            response = "📊 You haven't uploaded any transactions yet. Please upload your last 1 year bank transactions as a CSV file."
            twiml = MessagingResponse()
            twiml.message(response)
            return str(twiml)

        # Load business profile
        business_profile = load_profile()

        # Check if we need to collect profile information
        if needs_profile_info(business_profile):
            response = handle_profile_collection(user_input, user_id, business_profile)
            twiml = MessagingResponse()
            twiml.message(response)
            return str(twiml)

        # Load transactions
        bot.load_ledger_json("ledger/ledger.json")

        # Handle different types of uploads
        '''
        if media_url:
            # 1. Handle CSV Upload (Ledger)
            if media_type == "text/csv":
                response = handle_csv_upload(media_url, user_id)
                twiml = MessagingResponse()
                twiml.message(response)
                return str(twiml)

            # 2. Handle Invoice Image Upload
            if "image" in media_type or media_type == "application/pdf":
                from invoice_reminder.handler import upload_invoice_from_url
                response = upload_invoice_from_url(media_url, user_id)
                twiml = MessagingResponse()
                twiml.message(response)
                return str(twiml)
        '''

        # 3. Handle Text/Voice Commands
        if len(user_input) > 0:
            try:
                func_to_call, params = intent_router.get_function_to_call(user_input)
                print(f"Function to call: {func_to_call}")
                print(f"Parameters: {params}")
                
                response = func_to_call(**params)
                
                # For voice inputs, prepend the transcription acknowledgment
                if media_url and media_type and media_type.startswith('audio/'):
                    response = f"🎙 I heard: '{user_input}'\n\n{response}"
                    
            except Exception as processing_error:
                print(f"Command processing error: {processing_error}")
                response = "Sorry, I couldn't process that command. Please try again or type 'help' for available commands."
        else:
            response = "Please send a message, voice note, or upload a file."
    
        twiml = MessagingResponse()
        twiml.message(response)
        return str(twiml)
        
    except Exception as e:
        print(f"Handler error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a safe error response
        twiml = MessagingResponse()
        twiml.message("Sorry, there was an error processing your request. Please try again.")
        return str(twiml)
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files_to_cleanup:
            cleanup_temp_file(temp_file)

def handle_profile_collection(user_input: str, user_id: str, business_profile: dict) -> str:
    """
    Handle the business profile collection process via WhatsApp.
    """
    # Get the next field that needs to be filled
    next_field = get_next_missing_field(business_profile)
    
    if not next_field:
        # Profile is complete
        save_profile(business_profile)
        return "✅ Business profile completed! You can now use all features.\n\nTry:\n• 'forecast'\n• 'score'\n• 'simulate <what-if>'\n• 'tax <country>'"
    
    # If user provided input, try to save it for the current missing field
    if user_input:
        result = set_profile_field(business_profile, next_field, user_input)
        if result["success"]:
            save_profile(business_profile)
            # Check if there are more fields to collect
            next_field_after_save = get_next_missing_field(business_profile)
            if not next_field_after_save:
                return "✅ Business profile completed! You can now use all features.\n\nTry:\n• 'forecast'\n• 'score'\n• 'simulate <what-if>'\n• 'tax <country>'"
            else:
                return get_profile_question(next_field_after_save)
        else:
            return f"❌ {result['error']}\n\n{get_profile_question(next_field)}"
    
    # Ask for the next missing field
    welcome_msg = "📋 Let's set up your business profile to provide personalized insights:\n\n"
    return welcome_msg + get_profile_question(next_field)

def get_profile_question(field: str) -> str:
    """
    Generate appropriate question for each profile field.
    """
    questions = {
        "name": "What's your business name?",
        "country": "Which country is your business located in?",
        "industry": "What industry are you in? (e.g., Retail, Manufacturing, Services, etc.)",
        "region": "Is your business located in an Urban or Rural area?",
        "employees": "How many employees do you have? (Enter a number)",
        "years": "How many years has your business been operating? (Enter a number)"
    }
    
    return questions.get(field, f"Please provide your {field}:")

def handle_csv_upload(media_url: str, user_id: str = "default") -> str:
    try:
        result = file_manager.download_csv_from_twilio(media_url, user_id, twilio_auth)
        if not result["success"]:
            return f"❌ File download failed: {result['error']}"

        file_path = result["file_path"]
        validated_df = validate_csv(file_path)
        normalized_df = normalize_messy_csv(validated_df)
        standardized_df = map_columns(normalized_df)

        with LedgerManager() as ledger:
            ledger.bulk_apply_df(standardized_df)
            ledger._save_ledger()

        return (
            "✅ CSV uploaded and processed successfully!\n"
            "Try:\n"
            "• 'forecast'\n"
            "• 'score'\n"
            "• 'simulate <what-if>'\n"
            "• 'tax <country>'"
        )

    except Exception as e:
        return f"❌ Error processing CSV: {str(e)}"

def normalize_messy_csv(df: pd.DataFrame) -> pd.DataFrame:
    if 'Date' in df.columns:
        df['Date'] = df['Date'].ffill()
    df.dropna(how='all', inplace=True)
    df = df[df.notna().sum(axis=1) > 2]
    for col in ['Debit', 'Credit']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True).replace('', None).astype(float)
    return df

if __name__ == "__main__":
    bot.load_ledger_json("ledger/ledger.json")
    app.run(host="0.0.0.0", port=5000)