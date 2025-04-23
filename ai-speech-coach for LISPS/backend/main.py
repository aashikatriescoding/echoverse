from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import whisper
import os
import re
from pydub import AudioSegment
from youtube_transcript_api import YouTubeTranscriptApi
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime

# Temp directory for storing audio files
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper AI model
model = whisper.load_model("base")

# Store transcript lines and progress for session handling
session_data: Dict[str, List[str]] = {}
progress_data: Dict[str, List[Dict]] = {}  # Stores user_id: [{accuracy, timestamp, phrase}]

def extract_video_id(url: str):
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    return match.group(1) if match else None

@app.get("/")
async def home():
    return {"message": "AI Speech Coach Backend is running!"}

@app.get("/youtube_transcript/")
async def get_transcript(video_url: str, user_id: str = "default_user"):
    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return {"error": "Invalid YouTube URL format."}
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        session_data["transcript"] = [t["text"] for t in transcript]
        session_data["current_index"] = 0
        session_data["user_id"] = user_id  # Track user for progress
        return {"line": session_data["transcript"][0]}
    except Exception as e:
        return {"error": f"Could not fetch transcript: {str(e)}"}

@app.get("/next_line/")
async def get_next_line():
    if "transcript" not in session_data:
        return {"error": "No transcript found. Start a new session."}
    session_data["current_index"] += 1
    if session_data["current_index"] >= len(session_data["transcript"]):
        return {"line": "END OF TRANSCRIPT"}
    return {"line": session_data["transcript"][session_data["current_index"]]}

@app.get("/progress/")
async def get_progress(user_id: str = "default_user"):
    if user_id not in progress_data:
        return {"error": "No progress data found for this user."}
    return {"progress": progress_data[user_id]}

def detect_lisp_type(expected_sound: str, spoken_sound: str) -> Tuple[str, str]:
    lisp_types = {
        "s": {
            "type": "Interdental (Frontal) Lisp",
            "description": "Tongue protrudes between front teeth",
            "correction": "Keep tongue behind teeth"
        },
        "z": {
            "type": "Voiced Interdental Lisp",
            "description": "Tongue between teeth for 'z' sounds",
            "correction": "Practice buzzing 'zzz' with tongue behind teeth"
        },
        "th": {
            "type": "Th substitution",
            "description": "Using 'th' sound incorrectly",
            "correction": "Practice proper 's' or 'z' pronunciation"
        },
        "sh": {
            "type": "Palatal Lisp", 
            "description": "Tongue touches roof of mouth",
            "correction": "Lower tongue middle"
        }
    }
    
    if spoken_sound in lisp_types:
        info = lisp_types[spoken_sound]
        return (
            info["type"],
            f"{info['description']}. {info['correction']}"
        )
    return ("General Pronunciation Error", "Practice proper tongue placement")

def generate_lisp_exercise(lisp_type: str) -> str:
    exercises = {
        "Interdental (Frontal) Lisp": (
            "1. Say 't-t-t' to find alveolar ridge\n"
            "2. Practice 'see-saw' with tongue behind teeth"
        ),
        "Voiced Interdental Lisp": (
            "1. Buzz like a bee 'zzzz'\n"
            "2. Practice 'zoo, zebra, zero'"
        ),
        "Th substitution": (
            "1. Practice minimal pairs (thin/sin, then/zen)\n"
            "2. Use mirror to check tongue position"
        ),
        "Palatal Lisp": (
            "1. Lower middle of tongue\n"
            "2. Practice 't-d-n' sequences"
        )
    }
    return exercises.get(lisp_type, 
        "1. Slow repetition of problem words\n"
        "2. Mirror exercises for tongue placement")

def analyze_pronunciation(expected: str, spoken: str) -> Dict:
    errors = []
    expected_words = expected.lower().split()
    spoken_words = spoken.lower().split()
    
    lisp_map = {
        's': ['th', 'sh', 'f'],
        'z': ['th', 'dh'],
        'th': ['s', 't'],
        'sh': ['s']
    }
    
    for ew, sw in zip(expected_words, spoken_words):
        for target, mispronunciations in lisp_map.items():
            if target in ew:
                for mistake in mispronunciations:
                    if mistake in sw:
                        lisp_type, correction = detect_lisp_type(target, mistake)
                        errors.append({
                            "word": ew,
                            "expected": target,
                            "spoken": mistake,
                            "lisp_type": lisp_type,
                            "correction": correction,
                            "exercise": generate_lisp_exercise(lisp_type),
                            "severity": "high" if mistake in ['th', 'dh'] else "medium"
                        })
    
    return {
        "errors": errors,
        "word_match": SequenceMatcher(None, expected.lower(), spoken.lower()).ratio()
    }

def colorize_text(expected: str, spoken: str, errors: List[Dict]) -> str:
    expected_words = expected.split()
    spoken_words = spoken.split()
    colored_output = []
    
    for i, word in enumerate(expected_words):
        if i >= len(spoken_words):
            colored_output.append(f'<span style="color:red">{word}</span>')
            continue
            
        error_found = False
        for error in errors:
            if error["word"].lower() == word.lower():
                colored_output.append(
                    f'<span style="color:red" title="{error["correction"]}">{word}</span>'
                )
                error_found = True
                break
                
        if not error_found:
            if word.lower() == spoken_words[i].lower():
                colored_output.append(f'<span style="color:green">{word}</span>')
            else:
                colored_output.append(f'<span style="color:orange">{word}</span>')
    
    return " ".join(colored_output)

@app.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    try:
        if "transcript" not in session_data:
            return {"error": "No active transcript session."}
        
        current_line = session_data["transcript"][session_data["current_index"]]
        file_path = os.path.join(TEMP_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        if not file.filename.endswith(".wav"):
            audio = AudioSegment.from_file(file_path)
            wav_path = os.path.join(TEMP_DIR, "temp_audio.wav")
            audio.export(wav_path, format="wav")
            os.remove(file_path)
            file_path = wav_path
            
        result = model.transcribe(file_path)
        transcribed_text = result["text"]
        analysis = analyze_pronunciation(current_line, transcribed_text)
        
        # Store progress
        user_id = session_data.get("user_id", "default_user")
        if user_id not in progress_data:
            progress_data[user_id] = []
        
        progress_data[user_id].append({
            "accuracy": round(analysis["word_match"] * 100, 2),
            "timestamp": datetime.now().isoformat(),
            "phrase": current_line,
            "errors": len(analysis["errors"])
        })
        
        os.remove(file_path)
        
        return {
            "original_text": current_line,
            "spoken_text": transcribed_text,
            "colored_text": colorize_text(current_line, transcribed_text, analysis["errors"]),
            "analysis": analysis,
            "general_tips": [
                "💡 Practice 10-15 minutes daily for best results",
                "💡 Use a mirror to monitor tongue placement",
                "💡 Record yourself to track progress",
                "💡 Start slow, then increase speed gradually",
                "💡 Focus on accuracy before speed"
            ]
        }
    except Exception as e:
        return {"error": str(e)}







