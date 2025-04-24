import { useState, useEffect, useCallback } from 'react';
import { ReactMic } from 'react-mic';
import './App.css';

function App() {
  const [videoUrl, setVideoUrl] = useState("");
  const [currentLine, setCurrentLine] = useState("");
  const [recording, setRecording] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [progress, setProgress] = useState([]);
  const [userId] = useState("user_" + Math.random().toString(36).substr(2, 9));

  const fetchTranscript = async () => {
    if (!videoUrl.trim()) {
      alert("Please enter a YouTube URL!");
      return;
    }
    try {
      const response = await fetch(
        `http://localhost:8000/youtube_transcript/?video_url=${encodeURIComponent(videoUrl)}&user_id=${userId}`
      );
      const data = await response.json();
      if (data.error) {
        alert(data.error);
      } else {
        setCurrentLine(data.line);
        setAnalysis(null);
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
    } catch (error) {
      console.error("Error fetching next line:", error);
      alert("Failed to fetch next line.");
    }
  };

  const fetchProgress = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/progress/?user_id=${userId}`);
      const data = await response.json();
      if (data.progress) {
        setProgress(data.progress);
      }
    } catch (error) {
      console.error("Error fetching progress:", error);
    }
  }, [userId]);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress, analysis]);

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
      }
    } catch (error) {
      console.error("Error uploading audio:", error);
      alert("Failed to process speech.");
    }
  };

  const SpecificAdvice = ({ advice }) => {
    if (!advice || advice.length === 0) return null;
    
    return (
      <div className="specific-advice">
        <h3>Repetition Feedback</h3>
        <ul>
          {advice.map((item, index) => (
            <li key={index} className={item.includes('⚠️') ? "warning" : "tip"}>
              {item}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const ProgressDisplay = () => (
    <div className="progress-section">
      <h3>Your Progress</h3>
      {progress.length > 0 ? (
        <div className="progress-chart">
          {progress.slice().reverse().map((entry, i) => (
            <div key={i} className="progress-entry">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${entry.accuracy}%` }}
                ></div>
              </div>
              <div className="progress-details">
                <span>{entry.accuracy}% accuracy</span>
                <small>{new Date(entry.timestamp).toLocaleTimeString()}</small>
              </div>
              <p className="progress-phrase">{entry.phrase}</p>
            </div>
          ))}
        </div>
      ) : (
        <p>No progress data yet. Record some phrases to track your improvement!</p>
      )}
    </div>
  );

  return (
    <div className="app-container">
      <header>
        <h1>🎤 AI Fluency Coach</h1>
        <p className="subtitle">Improve your speech fluency with real-time feedback</p>
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
          <div className="metrics-container">
            <div className="metric">
              <h3>Accuracy</h3>
              <div className="metric-value">
                {Math.round(analysis.analysis.word_match * 100)}%
              </div>
            </div>
            
            <div className="metric">
              <h3>Disfluency Rate</h3>
              <div className="metric-value">
                {analysis.analysis.disfluency_rate.toFixed(2)}
              </div>
            </div>
          </div>
          
          <div className="feedback-section">
            <h3>Your Recording:</h3>
            <p className="user-recording">{analysis.spoken_text}</p>
            
            <SpecificAdvice advice={analysis.specific_advice} />
            
            <div className="general-tips">
              <h3>General Fluency Tips</h3>
              <ul>
                {analysis.general_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
      
      <ProgressDisplay />
      
      <div className="recording-section">
        <ReactMic
          record={recording}
          onStop={onStop}
          mimeType="audio/wav"
          visualSetting="frequencyBars"
          strokeColor="#4361ee"
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