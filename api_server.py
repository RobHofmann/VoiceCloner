import os
import json
from pathlib import Path
from typing import Optional
import soundfile as sf
import librosa
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from neuttsair.neutts import NeuTTSAir
import uuid

app = FastAPI(title="NeuTTS Air Voice Cloning API")

# Directories
VOICES_DIR = Path("/app/voices")
OUTPUTS_DIR = Path("/app/outputs")
STATIC_DIR = Path("/app/static")
VOICES_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Global TTS instance
tts = None
voice_profiles = {}

def init_tts():
    """Initialize the TTS model"""
    global tts
    if tts is None:
        backbone_device = os.getenv("BACKBONE_DEVICE", "cpu")
        codec_device = os.getenv("CODEC_DEVICE", "cpu")

        tts = NeuTTSAir(
            backbone_repo="neuphonic/neutts-air",
            backbone_device=backbone_device,
            codec_repo="neuphonic/neucodec",
            codec_device=codec_device
        )
    return tts

def load_voice_profiles():
    """Load existing voice profiles from disk"""
    global voice_profiles
    profiles_file = VOICES_DIR / "profiles.json"
    if profiles_file.exists():
        with open(profiles_file, 'r') as f:
            voice_profiles = json.load(f)
    return voice_profiles

def save_voice_profiles():
    """Save voice profiles to disk"""
    profiles_file = VOICES_DIR / "profiles.json"
    with open(profiles_file, 'w') as f:
        json.dump(voice_profiles, f, indent=2)

# Load profiles on startup
load_voice_profiles()

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize TTS on startup"""
    init_tts()
    print("NeuTTS Air API Server started successfully")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, 'r') as f:
            return f.read()
    return """
    <html>
        <body>
            <h1>NeuTTS Air Voice Cloning API</h1>
            <p>UI files not found. API is running at /docs</p>
        </body>
    </html>
    """

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "running",
        "service": "NeuTTS Air Voice Cloning API",
        "voices": len(voice_profiles)
    }

@app.post("/voices/clone")
async def clone_voice(
    file: UploadFile = File(...),
    voice_name: str = Form(...),
    reference_text: Optional[str] = Form(None)
):
    """
    Clone a voice from an uploaded audio file

    Args:
        file: Audio file (WAV recommended, 3-15 seconds, mono, 16-44kHz)
        voice_name: Name to identify this voice
        reference_text: Optional transcription of the reference audio
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.wav', '.mp3', '.flac', '.ogg', '.webm')):
            raise HTTPException(400, "Only audio files are supported (wav, mp3, flac, ogg, webm)")

        # Save uploaded file temporarily
        voice_id = str(uuid.uuid4())
        temp_path = VOICES_DIR / f"{voice_id}_temp"
        file_path = VOICES_DIR / f"{voice_id}.wav"

        contents = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(contents)

        # Load and preprocess audio
        # Convert to mono, resample to 24kHz (optimal for the model)
        audio, sr = librosa.load(str(temp_path), sr=24000, mono=True)

        # Normalize audio
        audio = audio / np.max(np.abs(audio))

        # Save preprocessed audio
        sf.write(str(file_path), audio, 24000)

        # Remove temporary file
        os.remove(temp_path)

        # Initialize TTS if needed
        init_tts()

        # Encode reference audio
        ref_codes = tts.encode_reference(str(file_path))

        # Save reference codes
        codes_path = VOICES_DIR / f"{voice_id}_codes.pt"
        import torch
        torch.save(ref_codes, codes_path)

        # Store voice profile
        voice_profiles[voice_name] = {
            "id": voice_id,
            "file": str(file_path),
            "codes_file": str(codes_path),
            "reference_text": reference_text,
            "original_filename": file.filename
        }
        save_voice_profiles()

        return {
            "status": "success",
            "message": f"Voice '{voice_name}' cloned successfully",
            "voice_id": voice_id,
            "voice_name": voice_name
        }

    except Exception as e:
        raise HTTPException(500, f"Error cloning voice: {str(e)}")

def chunk_text(text: str, max_chars: int = 200) -> list:
    """
    Split text into chunks for processing long text.
    Tries to split on sentence boundaries.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 2 <= max_chars:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]

@app.post("/tts/generate")
async def generate_speech(
    text: str = Form(...),
    voice_name: str = Form(...),
    output_filename: Optional[str] = Form(None)
):
    """
    Generate speech from text using a cloned voice

    Args:
        text: Text to convert to speech
        voice_name: Name of the cloned voice to use
        output_filename: Optional custom filename for output
    """
    try:
        # Check if voice exists
        if voice_name not in voice_profiles:
            raise HTTPException(404, f"Voice '{voice_name}' not found. Available voices: {list(voice_profiles.keys())}")

        # Initialize TTS if needed
        init_tts()

        # Load reference codes
        profile = voice_profiles[voice_name]
        import torch
        ref_codes = torch.load(profile["codes_file"])

        # Get reference text if available
        ref_text = profile.get("reference_text")

        # Split long text into chunks to avoid model limitations
        text_chunks = chunk_text(text, max_chars=200)

        # Generate speech for each chunk
        audio_segments = []
        for chunk in text_chunks:
            chunk_wav = tts.infer(chunk, ref_codes, ref_text)
            audio_segments.append(chunk_wav)

        # Concatenate all audio segments
        if len(audio_segments) > 1:
            wav = np.concatenate(audio_segments)
        else:
            wav = audio_segments[0]

        # Save output
        if output_filename is None:
            output_filename = f"{uuid.uuid4()}.wav"
        elif not output_filename.endswith('.wav'):
            output_filename += '.wav'

        output_path = OUTPUTS_DIR / output_filename
        sf.write(str(output_path), wav, 24000)

        return FileResponse(
            path=str(output_path),
            media_type="audio/wav",
            filename=output_filename
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating speech: {str(e)}")

@app.get("/voices")
async def list_voices():
    """List all cloned voices"""
    return {
        "voices": [
            {
                "name": name,
                "id": profile["id"],
                "original_file": profile["original_filename"],
                "has_reference_text": profile.get("reference_text") is not None
            }
            for name, profile in voice_profiles.items()
        ]
    }

@app.delete("/voices/{voice_name}")
async def delete_voice(voice_name: str):
    """Delete a cloned voice"""
    if voice_name not in voice_profiles:
        raise HTTPException(404, f"Voice '{voice_name}' not found")

    # Delete files
    profile = voice_profiles[voice_name]
    try:
        if os.path.exists(profile["file"]):
            os.remove(profile["file"])
        if os.path.exists(profile["codes_file"]):
            os.remove(profile["codes_file"])
    except Exception as e:
        print(f"Error deleting files: {e}")

    # Remove from profiles
    del voice_profiles[voice_name]
    save_voice_profiles()

    return {"status": "success", "message": f"Voice '{voice_name}' deleted"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "tts_initialized": tts is not None,
        "voices_count": len(voice_profiles),
        "backbone_device": os.getenv("BACKBONE_DEVICE", "cpu"),
        "codec_device": os.getenv("CODEC_DEVICE", "cpu")
    }
