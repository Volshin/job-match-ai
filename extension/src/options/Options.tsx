import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import './Options.css';

type Tab = 'settings' | 'profile' | 'priorities';

function Options() {
  const [tab, setTab] = useState<Tab>('settings');
  const [apiKey, setApiKey] = useState('');
  const [mcpUrl, setMcpUrl] = useState('');
  const [saved, setSaved] = useState(false);
  const [profileJson, setProfileJson] = useState('');
  const [prioritiesJson, setPrioritiesJson] = useState('');
  const [editorStatus, setEditorStatus] = useState('');

  useEffect(() => {
    chrome.storage.local.get(['apiKey', 'mcpUrl'], (result) => {
      if (result.apiKey) setApiKey(result.apiKey);
      if (result.mcpUrl) setMcpUrl(result.mcpUrl);
    });
  }, []);

  // Reload when tab or mcpUrl changes
  useEffect(() => {
    if (!mcpUrl) return;
    if (tab === 'profile') loadProfile();
    if (tab === 'priorities') loadPriorities();
  }, [tab, mcpUrl]);

  const loadProfile = async () => {
    try {
      setProfileJson('Загружаю...');
      const r = await fetch(`${mcpUrl}/profile`);
      setProfileJson(JSON.stringify(await r.json(), null, 2));
    } catch {
      setProfileJson('// Сервер недоступен. Проверь подключение.');
    }
  };

  const loadPriorities = async () => {
    try {
      setPrioritiesJson('Загружаю...');
      const r = await fetch(`${mcpUrl}/priorities`);
      setPrioritiesJson(JSON.stringify(await r.json(), null, 2));
    } catch {
      setPrioritiesJson('// Сервер недоступен. Проверь подключение.');
    }
  };

  const saveJson = async (endpoint: string, text: string) => {
    try {
      JSON.parse(text);
    } catch {
      setEditorStatus('❌ Невалидный JSON');
      return;
    }
    try {
      setEditorStatus('Сохраняю...');
      const r = await fetch(`${mcpUrl}/${endpoint}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: text,
      });
      if (!r.ok) throw new Error();
      setEditorStatus('✅ Сохранено');
      setTimeout(() => setEditorStatus(''), 2000);
    } catch {
      setEditorStatus('❌ Ошибка сохранения');
    }
  };

  const handleSaveSettings = async () => {
    if (mcpUrl) {
      try {
        const origin = new URL(mcpUrl).origin + '/*';
        await chrome.permissions.request({ origins: [origin] });
      } catch { /* ignore */ }
    }
    await chrome.storage.local.set({ apiKey, mcpUrl });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const testConnection = async () => {
    if (!mcpUrl) { alert('Введи URL сервера'); return; }
    try {
      const r = await fetch(`${mcpUrl}/context`);
      if (r.ok) {
        const d = await r.json();
        alert(d.profile ? '✅ Сервер доступен, профиль загружен' : '⚠️ Сервер доступен, но profile.json не найден');
      } else {
        alert('⚠️ Сервер вернул ' + r.status);
      }
    } catch (e) {
      alert('❌ Недоступен:\n' + (e as Error).message);
    }
  };

  return (
    <div className="options">
      <div className="container">
        <header><h1>Job Match AI</h1></header>

        <div className="tabs">
          {(['settings', 'profile', 'priorities'] as Tab[]).map(t => (
            <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
              {t === 'settings' ? 'Настройки' : t === 'profile' ? 'Профиль' : 'Приоритеты'}
            </button>
          ))}
        </div>

        {tab === 'settings' && (
          <>
            <div className="section">
              <h2>Anthropic API</h2>
              <div className="form-group">
                <label>API Key <span className="required">*</span></label>
                <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-ant-..." />
              </div>
            </div>
            <div className="section">
              <h2>Career Server</h2>
              <div className="form-group">
                <label>URL сервера</label>
                <input type="url" value={mcpUrl} onChange={e => setMcpUrl(e.target.value)} placeholder="http://100.64.0.2:8765" />
                <button className="secondary-btn" onClick={testConnection}>Проверить подключение</button>
              </div>
            </div>
            <div className="actions">
              <button className="primary-btn" onClick={handleSaveSettings}>
                {saved ? '✅ Сохранено' : 'Сохранить'}
              </button>
            </div>
          </>
        )}

        {(tab === 'profile' || tab === 'priorities') && (
          <div className="section">
            {!mcpUrl ? (
              <p className="help-text">Укажи URL сервера во вкладке Настройки и сохрани.</p>
            ) : (
              <>
                <div className="editor-actions">
                  <button className="secondary-btn" onClick={tab === 'profile' ? loadProfile : loadPriorities}>
                    Обновить с сервера
                  </button>
                  <button className="primary-btn" onClick={() =>
                    saveJson(tab, tab === 'profile' ? profileJson : prioritiesJson)
                  }>
                    Сохранить на сервер
                  </button>
                  {editorStatus && <span className="editor-status">{editorStatus}</span>}
                </div>
                <textarea
                  className="json-editor"
                  value={tab === 'profile' ? profileJson : prioritiesJson}
                  onChange={e => tab === 'profile' ? setProfileJson(e.target.value) : setPrioritiesJson(e.target.value)}
                  spellCheck={false}
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Options />
  </React.StrictMode>
);
