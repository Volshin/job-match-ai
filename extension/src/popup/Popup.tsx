import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import './Popup.css';

interface AnalysisResult {
  match_score: number;
  key_matches: string[];
  gaps: string[];
  red_flags: string[];
  green_flags: string[];
  recommendation: 'Apply' | 'Skip' | 'Consider';
  reasoning_ru: string;
  error?: string;
}

function Popup() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    chrome.runtime.sendMessage({ type: 'getLastAnalysis' }, (response) => {
      setAnalysis(response);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="popup">
        <div className="loading">Загрузка...</div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="popup">
        <div className="empty-state">
          <h2>Job Match AI</h2>
          <p>Выделите текст вакансии на странице и нажмите правой кнопкой:</p>
          <p className="highlight">🎯 Analyze Job Match</p>
          <button onClick={() => chrome.runtime.openOptionsPage()}>
            ⚙️ Настройки
          </button>
        </div>
      </div>
    );
  }

  if (analysis.error) {
    return (
      <div className="popup">
        <div className="error">
          <h3>❌ Ошибка</h3>
          <p>{analysis.error}</p>
          <button onClick={() => chrome.runtime.openOptionsPage()}>
            Проверить настройки
          </button>
        </div>
      </div>
    );
  }

  const getRecommendationColor = (rec: string) => {
    if (rec === 'Apply') return '#22c55e';
    if (rec === 'Skip') return '#ef4444';
    return '#f59e0b';
  };

  return (
    <div className="popup">
      <div className="header">
        <h2>Job Match AI</h2>
        <button
          className="close-btn"
          onClick={() => {
            chrome.runtime.sendMessage({ type: 'clearAnalysis' });
            window.close();
          }}
        >
          ✕
        </button>
      </div>

      <div className="score-section">
        <div className="score-circle" style={{ borderColor: getRecommendationColor(analysis.recommendation) }}>
          <div className="score-value">{analysis.match_score}%</div>
        </div>
        <div className="recommendation" style={{ color: getRecommendationColor(analysis.recommendation) }}>
          {analysis.recommendation === 'Apply' && '✅ Подавать'}
          {analysis.recommendation === 'Skip' && '❌ Пропустить'}
          {analysis.recommendation === 'Consider' && '🤔 Подумать'}
        </div>
      </div>

      <div className="reasoning">
        <strong>Анализ:</strong>
        <p>{analysis.reasoning_ru}</p>
      </div>

      {analysis.key_matches.length > 0 && (
        <div className="section">
          <h3>✅ Совпадения</h3>
          <ul>
            {analysis.key_matches.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.gaps.length > 0 && (
        <div className="section">
          <h3>⚠️ Gaps</h3>
          <ul>
            {analysis.gaps.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.red_flags.length > 0 && (
        <div className="section red-flags">
          <h3>🚩 Red Flags</h3>
          <ul>
            {analysis.red_flags.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.green_flags.length > 0 && (
        <div className="section green-flags">
          <h3>🟢 Green Flags</h3>
          <ul>
            {analysis.green_flags.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="footer">
        <button onClick={() => chrome.runtime.openOptionsPage()}>
          ⚙️ Настройки
        </button>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Popup />
  </React.StrictMode>
);
