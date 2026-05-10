import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import './Options.css';

function Options() {
  const [apiKey, setApiKey] = useState('');
  const [mcpUrl, setMcpUrl] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Load saved settings
    chrome.storage.local.get(['apiKey', 'mcpUrl'], (result) => {
      if (result.apiKey) setApiKey(result.apiKey);
      if (result.mcpUrl) setMcpUrl(result.mcpUrl);
    });
  }, []);

  const handleSave = async () => {
    await chrome.storage.local.set({ apiKey, mcpUrl });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const testMcpConnection = async () => {
    if (!mcpUrl) {
      alert('Введите MCP URL');
      return;
    }

    try {
      const response = await fetch(mcpUrl, { method: 'HEAD' });
      if (response.ok) {
        alert('✅ MCP сервер доступен');
      } else {
        alert('⚠️ MCP сервер вернул ошибку: ' + response.status);
      }
    } catch (error) {
      alert('❌ Не удалось подключиться к MCP серверу:\n' + (error as Error).message);
    }
  };

  return (
    <div className="options">
      <div className="container">
        <header>
          <h1>Job Match AI</h1>
          <p>Настройки анализа вакансий</p>
        </header>

        <div className="section">
          <h2>Anthropic API</h2>
          <div className="form-group">
            <label htmlFor="apiKey">
              API Key <span className="required">*</span>
            </label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-ant-..."
            />
            <p className="help-text">
              Получить ключ можно в{' '}
              <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer">
                Anthropic Console
              </a>
            </p>
          </div>
        </div>

        <div className="section">
          <h2>MCP Server (опционально)</h2>
          <div className="form-group">
            <label htmlFor="mcpUrl">MCP Server URL</label>
            <input
              id="mcpUrl"
              type="url"
              value={mcpUrl}
              onChange={(e) => setMcpUrl(e.target.value)}
              placeholder="https://mcp.yourdomain.com"
            />
            <p className="help-text">
              URL MCP сервера с карьерным профилем на Raspberry Pi. Оставьте пустым для работы без MCP (используется
              только статичный system prompt).
            </p>
            <button className="secondary-btn" onClick={testMcpConnection}>
              Проверить подключение
            </button>
          </div>
        </div>

        <div className="info-box">
          <h3>ℹ️ Как это работает</h3>
          <ol>
            <li>Выделите текст вакансии на странице (LinkedIn, HH.ru, Habr Career, и т.д.)</li>
            <li>Кликните правой кнопкой → <strong>"🎯 Analyze Job Match"</strong></li>
            <li>Расширение отправит запрос к Claude API с вашим профилем из MCP сервера</li>
            <li>Результат появится в popup: match score, flags, recommendation</li>
          </ol>
        </div>

        <div className="actions">
          <button className="primary-btn" onClick={handleSave}>
            {saved ? '✅ Сохранено' : 'Сохранить'}
          </button>
        </div>

        <div className="footer-info">
          <p>
            <strong>Job Match AI v0.1.0</strong>
          </p>
          <p>
            Документация:{' '}
            <a href="https://github.com/yourusername/job-match-ai" target="_blank" rel="noopener noreferrer">
              GitHub
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Options />
  </React.StrictMode>
);
