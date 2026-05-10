import Anthropic from '@anthropic-ai/sdk';

// System prompt для анализа вакансий
const SYSTEM_PROMPT = `Ты эксперт по подбору SAP/Enterprise-вакансий для DACH-рынка.

На входе:
1. Карьерный профиль кандидата (через MCP tools)
2. Текст вакансии

Проанализируй match и верни строго JSON без префикса/суффикса:
{
  "match_score": 0-100,
  "key_matches": ["пункт 1", "пункт 2", ...],
  "gaps": ["что не хватает 1", "что не хватает 2", ...],
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
- SAP + AI integration

Учитывай текущие constraints из MCP tools (location preferences, language level, health considerations).`;

// Context menu handler
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
      // Get settings
      const settings = await chrome.storage.local.get(['apiKey', 'mcpUrl']);
      
      if (!settings.apiKey) {
        chrome.action.openPopup();
        return;
      }

      // Analyze job
      const result = await analyzeJob(info.selectionText, settings);
      
      // Store result
      await chrome.storage.local.set({ lastAnalysis: result });
      
      // Open popup to show results
      chrome.action.openPopup();
    } catch (error) {
      console.error('Analysis failed:', error);
      await chrome.storage.local.set({
        lastAnalysis: {
          error: error instanceof Error ? error.message : 'Unknown error',
        },
      });
      chrome.action.openPopup();
    }
  }
});

async function analyzeJob(jobText: string, settings: { apiKey: string; mcpUrl?: string }) {
  const client = new Anthropic({
    apiKey: settings.apiKey,
    dangerouslyAllowBrowser: true,
  });

  const requestBody: any = {
    model: 'claude-sonnet-4-20250514',
    max_tokens: 2000,
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: 'user',
        content: `JOB DESCRIPTION:\n\n${jobText}\n\nПроанализируй match с учётом профиля кандидата.`,
      },
    ],
  };

  // Add MCP server if configured
  if (settings.mcpUrl) {
    requestBody.mcp_servers = [
      {
        type: 'url',
        url: settings.mcpUrl,
        name: 'career-context',
      },
    ];
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': settings.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
      'content-type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'API request failed');
  }

  const data = await response.json();
  const textContent = data.content.find((c: any) => c.type === 'text')?.text || '';
  
  // Parse JSON response
  const jsonMatch = textContent.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error('Failed to parse JSON response from Claude');
  }

  return JSON.parse(jsonMatch[0]);
}

// Message handler for popup/options communication
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'getLastAnalysis') {
    chrome.storage.local.get(['lastAnalysis']).then((result) => {
      sendResponse(result.lastAnalysis || null);
    });
    return true; // Async response
  }
  
  if (message.type === 'clearAnalysis') {
    chrome.storage.local.remove(['lastAnalysis']).then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
});
