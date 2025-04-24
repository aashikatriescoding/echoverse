import os
import whisper
import torch
from flask import Flask, request, jsonify
import re

app = Flask(__name__)

# Load Whisper model
model = whisper.load_model("base")

# Function to detect stuttering patterns
def detect_stuttering(text):
    stutter_patterns = [
        r'\b(\w+)(\s+\1)+\b',  # Repeated words (like "I-I-I")
        r'(\w)-\1'             # Broken words (like "s-s-sorry")
    ]
    issues = []
    for pattern in stutter_patterns:
        matches = re.findall(pattern, text)
        if matches:
            issues.extend(matches)
    return issues

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    audio_file = request.files['file']
    audio_path = 'temp_audio.wav'
    audio_file.save(audio_path)
    
    # Transcribe using Whisper
    result = model.transcribe(audio_path)
    transcription = result['text']
    
    # Detect stuttering
    stuttering_issues = detect_stuttering(transcription)
    
    response = {
        'transcription': transcription,
        'stuttering_detected': stuttering_issues
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
