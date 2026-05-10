#!/usr/bin/env python3
"""
Job Match AI - MCP Server
Предоставляет tools для Claude API для анализа job match.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("career-context")

# Data paths
DATA_DIR = Path(__file__).parent / "data"
PROFILE_FILE = DATA_DIR / "profile.json"
PRIORITIES_FILE = DATA_DIR / "priorities.json"
BLACKLIST_FILE = DATA_DIR / "blacklist.json"
TRACKER_FILE = DATA_DIR / "tracker.jsonl"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


@mcp.tool()
def get_career_context() -> Dict:
    """
    Возвращает полный карьерный профиль кандидата.
    
    Включает:
    - Professional background (опыт, роли, компетенции)
    - Skills (SAP modules, programming languages, tools)
    - Target roles (желаемые позиции)
    - Location preferences
    - Language levels
    
    Returns:
        Dict: Полный карьерный профиль
    """
    if not PROFILE_FILE.exists():
        return {
            "error": "Profile not found",
            "message": "Create profile.json in mcp-server/data/"
        }
    
    with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


@mcp.tool()
def get_current_priorities() -> Dict:
    """
    Возвращает актуальные constraints и приоритеты поиска работы.
    
    Включает:
    - Location readiness (current city, relocation plans, remote preferences)
    - Language levels (German A2, English C1)
    - Health constraints (remote work preference due to protocols)
    - Timeline (available from date)
    - Deal breakers (on-site only, fluent German required, etc.)
    - Green flags (AI focus, Series A-B, etc.)
    
    Обновляется вручную когда меняется жизненная ситуация.
    
    Returns:
        Dict: Текущие приоритеты и constraints
    """
    if not PRIORITIES_FILE.exists():
        return {
            "status": "active_search",
            "updated": datetime.now().isoformat(),
            "location": {
                "current": "Mannheim, Germany",
                "remote_preference": "preferred",
                "relocation_ready": True,
                "relocation_timeline_days": 14
            },
            "languages": {
                "english": "C1",
                "german": "A2",
                "russian": "native"
            },
            "constraints": {
                "health_protocol_active": True,
                "remote_async_preferred": True,
                "fluent_german_not_ready": True
            },
            "red_flags": [
                "On-site only без remote опции",
                "Fluent German required (пока A2 level)",
                "Junior tasks под видом senior role",
                "Mass recruiter без персонализации"
            ],
            "green_flags": [
                "Remote/hybrid work",
                "AI/S4HANA modernization",
                "Series A-B stage, scaleup",
                "English-speaking team",
                "Strategic/architectural role"
            ]
        }
    
    with open(PRIORITIES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


@mcp.tool()
def get_blacklisted_companies() -> List[str]:
    """
    Возвращает список компаний/рекрутеров для фильтрации.
    
    Включает:
    - Спамные рекрутеры (mass outreach без чтения requirements)
    - Компании с плохим опытом (неадекватный interview process)
    - Агентства, которые не читают clarifying questions
    
    Returns:
        List[str]: Список компаний/рекрутеров для избежания
    """
    if not BLACKLIST_FILE.exists():
        return []
    
    with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("companies", [])


@mcp.tool()
def save_analysis(
    job_url: str,
    company: str,
    position: str,
    match_score: int,
    recommendation: str,
    reasoning: str,
    red_flags: List[str],
    green_flags: List[str]
) -> str:
    """
    Сохраняет результат анализа вакансии в application tracker.
    
    Args:
        job_url: URL вакансии
        company: Название компании
        position: Название позиции
        match_score: Match score 0-100
        recommendation: Apply/Skip/Consider
        reasoning: Reasoning на русском
        red_flags: Список red flags
        green_flags: Список green flags
    
    Returns:
        str: Confirmation message
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "job_url": job_url,
        "company": company,
        "position": position,
        "match_score": match_score,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "red_flags": red_flags,
        "green_flags": green_flags
    }
    
    # Append to JSONL file
    with open(TRACKER_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    return f"✅ Analysis saved: {company} - {position} ({match_score}% match, {recommendation})"


if __name__ == "__main__":
    # Run MCP server on HTTP (для доступа через Cloudflare Tunnel)
    mcp.run(transport="http", host="0.0.0.0", port=8765)
