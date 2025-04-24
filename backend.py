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

# Temp directory
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = whisper.load_model("base")
session_data: Dict[str, List[str]] = {}
progress_data: Dict[str, List[Dict]] = {}

@app.get("/")
async def home():
    return {"message": "AI Fluency Coach Backend"}

def extract_video_id(url: str):
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    return match.group(1) if match else None

@app.get("/youtube_transcript/")
async def get_transcript(video_url: str, user_id: str = "default_user"):
    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return {"error": "Invalid YouTube URL"}
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        session_data["transcript"] = [t["text"] for t in transcript]
        session_data["current_index"] = 0
        session_data["user_id"] = user_id
        return {"line": session_data["transcript"][0]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/next_line/")
async def get_next_line():
    if "transcript" not in session_data:
        return {"error": "No active session"}
    session_data["current_index"] += 1
    if session_data["current_index"] >= len(session_data["transcript"]):
        return {"line": "END OF TRANSCRIPT"}
    return {"line": session_data["transcript"][session_data["current_index"]]}

@app.get("/progress/")
async def get_progress(user_id: str = "default_user"):
    if user_id not in progress_data:
        return {"error": "No progress data"}
    return {"progress": progress_data[user_id]}

def detect_stutter_type(pattern: str):
    stutter_types = {
        "repetition": {
            "type": "Repetition",
            "description": "Repeating sounds or words",
            "correction": "Use gentle onset techniques"
        },
        "prolongation": {
            "type": "Prolongation", 
            "description": "Extending sounds too long",
            "correction": "Practice controlled breathing"
        },
        "block": {
            "type": "Block",
            "description": "Speech blocks or pauses",
            "correction": "Use light articulatory contacts"
        }
    }
    return stutter_types.get(pattern, ("General Disfluency", "Practice slow speech"))

def analyze_repetitions(spoken_text: str) -> List[Dict]:
    words = spoken_text.lower().split()
    repetitions = []
    i = 0
    while i < len(words):
        current_word = words[i]
        count = 1
        while i + count < len(words) and words[i + count] == current_word:
            count += 1
        if count > 1:
            repetitions.append({
                "word": current_word,
                "count": count,
                "position": i,
                "advice": generate_rep_advice(current_word, count)
            })
            i += count
        else:
            i += 1
    return repetitions

def generate_rep_advice(word: str, count: int) -> str:
    if count > 2:
        return (
            f"⚠️ Excessive repetition: '{word}' {count}x. "
            f"Try: 1) Pause before speaking 2) Slow exhale 3) Light contact"
        )
    return (
        f"🔹 Repeated '{word}'. "
        f"Try: 1) Gentle onset 2) Stretch vowel sounds"
    )

def analyze_fluency(expected: str, spoken: str) -> Dict:
    errors = []
    repetitions = analyze_repetitions(spoken)
    
    # Patterns to detect
    patterns = {
        "repetition": r"\b(\w{1,3})\1+\b",
        "prolongation": r"\b\w*([a-zA-Z])\1{3,}\w*\b",
        "block": r"\b\w*[^aeiouAEIOU\s]\s{2,}\w*\b"
    }
    
    for pattern_type, regex in patterns.items():
        matches = re.finditer(regex, spoken.lower())
        for match in matches:
            stutter_type, correction = detect_stutter_type(pattern_type)
            errors.append({
                "segment": match.group(),
                "pattern": pattern_type,
                "stutter_type": stutter_type,
                "correction": correction,
                "severity": "high" if pattern_type in ["block", "prolongation"] else "medium"
            })
    
    spoken_words = spoken.split()
    expected_words = expected.split()
    word_match = SequenceMatcher(None, expected.lower(), spoken.lower()).ratio()
    disfluency_rate = (len(errors) + len(repetitions)) / max(1, len(spoken_words))
    
    return {
        "errors": errors,
        "repetitions": repetitions,
        "word_match": word_match,
        "disfluency_rate": disfluency_rate,
        "speech_rate": len(spoken_words) / 10  # words per second
    }

def colorize_text(expected: str, spoken: str, errors: List[Dict], reps: List[Dict]) -> str:
    words = spoken.split()
    colored = []
    rep_positions = {r['position']: r for r in reps}
    
    i = 0
    while i < len(words):
        if i in rep_positions:
            rep = rep_positions[i]
            colored.append(
                f'<span class="repeated-word" title="Repeated {rep["count"]} times">'
                f'{words[i]}</span>'
            )
            i += rep['count']
            continue
            
        error_found = False
        for error in errors:
            if error["segment"].lower() in words[i].lower():
                colored.append(
                    f'<span style="color:red" title="{error["correction"]}">{words[i]}</span>'
                )
                error_found = True
                break
                
        if not error_found:
            if words[i].lower() in expected.lower():
                colored.append(f'<span style="color:green">{words[i]}</span>')
            else:
                colored.append(f'<span style="color:orange">{words[i]}</span>')
        i += 1
    
    return " ".join(colored)

@app.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    try:
        if "transcript" not in session_data:
            return {"error": "No active session"}
        
        current_line = session_data["transcript"][session_data["current_index"]]
        file_path = os.path.join(TEMP_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        if not file.filename.endswith(".wav"):
            audio = AudioSegment.from_file(file_path)
            wav_path = os.path.join(TEMP_DIR, "temp.wav")
            audio.export(wav_path, format="wav")
            os.remove(file_path)
            file_path = wav_path
            
        result = model.transcribe(file_path)
        transcribed = result["text"]
        analysis = analyze_fluency(current_line, transcribed)
        
        # Store progress
        user_id = session_data.get("user_id", "default_user")
        if user_id not in progress_data:
            progress_data[user_id] = []
        
        progress_data[user_id].append({
            "accuracy": round(analysis["word_match"] * 100, 2),
            "disfluency": round(analysis["disfluency_rate"], 3),
            "timestamp": datetime.now().isoformat(),
            "phrase": current_line
        })
        
        os.remove(file_path)
        
        return {
            "original_text": current_line,
            "spoken_text": transcribed,
            "colored_text": colorize_text(current_line, transcribed, analysis["errors"], analysis["repetitions"]),
            "analysis": analysis,
            "specific_advice": [r["advice"] for r in analysis["repetitions"]],
            "general_tips": [
                "💡 Practice with a metronome",
                "💡 Use delayed auditory feedback",
                "💡 Record and review daily"
            ]
        }
    except Exception as e:
        return {"error": str(e)}