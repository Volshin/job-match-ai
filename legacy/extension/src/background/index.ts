import Anthropic from '@anthropic-ai/sdk';

const SYSTEM_PROMPT = `Ты эксперт по подбору SAP/Enterprise-вакансий для DACH-рынка.

На входе:
1. Карьерный профиль кандидата (в секции CAREER CONTEXT)
2. Текст вакансии

Проанализируй match и верни строго JSON без префикса/суффикса:
{
  "company": "название компании из вакансии или Unknown",
  "position": "название должности из вакансии",
  "match_score": 0-100,
  "key_matches": ["пункт 1", "пункт 2", ...],
  "gaps": ["что не хватает 1", ...],
  "red_flags": ["негативный фактор 1", ...],
  "green_flags": ["позитивный фактор 1", ...],
  "recommendation": "Apply" | "Skip" | "Consider",
  "reasoning_ru": "2-3 предложения: почему именно так, с учётом карьерной стратегии и текущих constraints"
}

**Red Flags** (deal breakers):
- On-site only без remote опции
- "Fluent German required" (кандидат пока A2)
- Junior task list под видом senior role
- Mass recruiter без персонализации
- Чистый maintenance без стратегического компонента

**Green Flags** (сильные позитивы):
- Remote/hybrid work
- AI/S/4HANA modernization focus
- Series A-B stage, scaleup, greenfield
- English-speaking team
- Project autonomy, strategic role
- SAP + AI integration`;

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'analyze-job',
    title: '🎯 Analyze Job Match',
    contexts: ['selection'],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'analyze-job' && info.selectionText) {
    try {
      const settings = await chrome.storage.local.get(['apiKey', 'mcpUrl']);
      if (!settings.apiKey) {
        chrome.action.openPopup();
        return;
      }
      const result = await analyzeJob(info.selectionText, info.pageUrl || '', settings);
      await chrome.storage.local.set({ lastAnalysis: result });
      await openPopupSafe();
    } catch (error) {
      await chrome.storage.local.set({
        lastAnalysis: { error: error instanceof Error ? error.message : 'Unknown error' },
      });
      await openPopupSafe();
    }
  }
});

async function openPopupSafe() {
  try {
    const win = await chrome.windows.getLastFocused({ windowTypes: ['normal'] });
    await chrome.action.openPopup({ windowId: win.id! });
  } catch {
    await chrome.action.setBadgeText({ text: '!' });
    await chrome.action.setBadgeBackgroundColor({ color: '#6366f1' });
  }
}

async function fetchCareerContext(mcpUrl: string): Promise<string> {
  const response = await fetch(`${mcpUrl}/context`);
  if (!response.ok) throw new Error(`Career server error: ${response.status}`);
  const data = await response.json();
  return JSON.stringify(data, null, 2);
}

async function saveToTracker(mcpUrl: string, result: any, jobUrl: string) {
  try {
    await fetch(`${mcpUrl}/analysis`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        job_url: jobUrl,
        company: result.company || 'Unknown',
        position: result.position || 'Unknown',
        match_score: result.match_score,
        recommendation: result.recommendation,
        reasoning: result.reasoning_ru,
        red_flags: result.red_flags || [],
        green_flags: result.green_flags || [],
      }),
    });
  } catch {
    // tracker save is non-critical, silently ignore
  }
}

async function analyzeJob(jobText: string, jobUrl: string, settings: { apiKey: string; mcpUrl?: string }) {
  let systemPrompt = SYSTEM_PROMPT;

  if (settings.mcpUrl) {
    const context = await fetchCareerContext(settings.mcpUrl);
    systemPrompt += `\n\n## CAREER CONTEXT:\n\`\`\`json\n${context}\n\`\`\`\n\nИспользуй этот контекст — особенно priorities.red_flags, priorities.deal_breakers, priorities.salary.`;
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': settings.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 2000,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: `JOB DESCRIPTION:\n\n${jobText}\n\nПроанализируй match с учётом профиля кандидата.`,
        },
      ],
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'API request failed');
  }

  const data = await response.json();
  const textContent = data.content.find((c: any) => c.type === 'text')?.text || '';
  const jsonMatch = textContent.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error('Failed to parse JSON response from Claude');

  const result = JSON.parse(jsonMatch[0]);

  if (settings.mcpUrl) {
    await saveToTracker(settings.mcpUrl, result, jobUrl);
  }

  return result;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'getLastAnalysis') {
    chrome.storage.local.get(['lastAnalysis']).then((result) => {
      sendResponse(result.lastAnalysis || null);
    });
    return true;
  }
  if (message.type === 'clearAnalysis') {
    chrome.storage.local.remove(['lastAnalysis']).then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
});
