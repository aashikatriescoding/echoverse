
import { useState } from 'react';
import { ReactMic } from 'react-mic';
import "./App.css";
function App() {
  const [videoUrl, setVideoUrl] = useState("");
  const [currentLine, setCurrentLine] = useState("");
  const [recording, setRecording] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const fetchTranscript = async () => {
    if (!videoUrl.trim()) {
      alert("Please enter a valid YouTube URL!");
      return;
    }
    try {
      const response = await fetch(
        `http://localhost:8000/youtube_transcript/?video_url=${encodeURIComponent(videoUrl)}`
      );
      const data = await response.json();
      if (data.error) {
        alert(data.error);
      } else {
        setCurrentLine(data.line);
        setAnalysis(null);
        setShowDetails(false);
      }
    } catch (error) {
      console.error("Error fetching transcript:", error);
      alert("Failed to fetch transcript.");
    }
  };
  const fetchNextLine = async () => {
    try {
      const response = await fetch("http://localhost:8000/next_line/");
      const data = await response.json();
      setCurrentLine(data.line);
      setAnalysis(null);
      setShowDetails(false);
    } catch (error) {
      console.error("Error fetching next line:", error);
      alert("Failed to fetch next line.");
    }
  };
  const startRecording = () => setRecording(true);
  const stopRecording = () => setRecording(false);
  const onStop = async (recordedBlob) => {
    const formData = new FormData();
    const file = new File([recordedBlob.blob], "audio.wav", { type: "audio/wav" });
    formData.append("file", file);
    
    try {
      const response = await fetch("http://localhost:8000/upload/", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (data.error) {
        alert(data.error);
      } else {
        setAnalysis(data);
        setShowDetails(false); // Reset details visibility when new analysis comes in
      }
    } catch (error) {
      console.error("Error uploading audio:", error);
      alert("Failed to process speech.");
    }
  };
  const renderErrorDetails = (error, index) => (
    <div key={index} className="error-detail">
      <h4>❌ {error.word} 
        <span className="phoneme">(Expected: {error.expected}, Spoken: {error.spoken})</span>
      </h4>
      <p><strong>Type:</strong> {error.lisp_type}</p>
      <p><strong>Correction:</strong> {error.correction}</p>
      <div className="exercise">
        <strong>Exercises:</strong>
        <pre>{error.exercise}</pre>
      </div>
    </div>
  );
  return (
    <div className="app-container">
      <header>
        <h1>🎤 AI Speech Coach</h1>
        <p className="subtitle">Improve your pronunciation with real-time feedback</p>
      </header>
      
      <div className="input-section">
        <input
          type="text"
          placeholder="Enter YouTube video URL..."
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
        />
        <button onClick={fetchTranscript}>Load Transcript</button>
      </div>
      
      <div className="current-line">
        <h2>Current Phrase:</h2>
        <div className="phrase-box">
          {analysis ? (
            <div dangerouslySetInnerHTML={{ __html: analysis.colored_text }} />
          ) : (
            <p>{currentLine || "No phrase loaded"}</p>
          )}
        </div>
      </div>
      
      {analysis && (
        <div className="results-section">
          <div className="accuracy-meter">
            <h3>Pronunciation Accuracy: 
              <span> {Math.round(analysis.analysis.word_match * 100)}%</span>
            </h3>
            <div className="meter-bar">
              <div 
                className="meter-fill"
                style={{ width: `${Math.round(analysis.analysis.word_match * 100)}%` }}
              ></div>
            </div>
          </div>
          
          <div className="feedback-section">
            <h3>Your Recording:</h3>
            <p className="user-recording">{analysis.spoken_text}</p>
            
            {analysis.analysis.errors.length > 0 && (
              <>
                <button 
                  className="toggle-details"
                  onClick={() => setShowDetails(!showDetails)}
                >
                  {showDetails ? "Hide Details" : "Show Detailed Feedback"}
                </button>
                {showDetails && (
                  <div className="detailed-feedback">
                    <h3>Pronunciation Errors Found:</h3>
                    {analysis.analysis.errors.map(renderErrorDetails)}
                  </div>
                )}
              </>
            )}
            
            <div className="general-tips">
              <h3>General Practice Tips</h3>
              <ul>
                {analysis.general_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
      
      <div className="recording-section">
        <ReactMic
          record={recording}
          onStop={onStop}
          mimeType="audio/wav"
          visualSetting="frequencyBars"
          strokeColor="#4a89dc"
          backgroundColor="#f5f7fa"
        />
        <div className="controls">
          <button 
            onClick={startRecording} 
            disabled={recording || !currentLine}
            className={recording ? "active" : ""}
          >
            {recording ? "🎤 Recording..." : "Start Recording"}
          </button>
          <button 
            onClick={stopRecording} 
            disabled={!recording}
          >
            Stop Recording
          </button>
          <button onClick={fetchNextLine}>
            Next Phrase
          </button>
        </div>
      </div>
    </div>
  );
}
export default App;
