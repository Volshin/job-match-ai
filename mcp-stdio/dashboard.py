"""
Dashboard builder for the vacancy registry.

Pure functions: rows (list of dicts, as read from vacancies.csv) in,
one self-contained HTML file out. Calculation logic follows pet9_dashboard_build.py.
"""

from datetime import date, datetime, timedelta
from collections import Counter
import html
import json

D3_URL = "https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"
D3_SRI = "sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i"

APPLIED   = ("откликнулся", "в переписке", "интервью", "отказ", "затухла")
REPLIED   = ("в переписке", "интервью", "отказ")
OPEN      = ("новая", "к отклику", "отложена (язык)", "откликнулся")
LEVELS    = ("Project Manager", "Team Lead", "Application Manager",
             "IT Business Partner", "Architect / Consultant", "Прочее")

STATUS_LABELS = {
    "отклонена": "Отсеяна до отклика", "отказ": "Отказ", "к отклику": "К отклику",
    "новая": "Новая", "затухла": "Затухла", "в переписке": "В переписке",
    "отложена (язык)": "Отложена по языку", "откликнулся": "Откликнулся",
    "интервью": "Интервью",
}
LANG_LABELS = {
    "DE обязателен": "Немецкий обязателен", "EN": "Английский",
    "не указан": "Язык не указан", "EN+DE желателен": "Английский, немецкий желателен",
}

# Substrings (lower-case) that identify a country in the free-form Локация column.
_COUNTRY_HINTS = {
    "NL": ("nl", "netherlands", "holland", "amsterdam", "rotterdam", "utrecht", "leiden",
           "amstelveen", "arnhem", "middelburg", "velsen", "kerkrade", "hertogenbosch",
           "maarssen", "nieuwerkerk", "etten-leur"),
    "DE": ("germany", "германия", "мангейм", "mannheim", "munich", "münchen", "hamburg",
           "frankfurt", "düsseldorf", "herzogenaurach", "darmstadt", "leon-rot", "walldorf",
           "garching", "bochum", "hannover", "köln", "cologne", "ulm", "memmingen", "berlin",
           "stuttgart", "würzburg", "erlangen", "friedrichshafen", "maulburg", "marktoberdorf",
           "nürnberg", "metzingen", "ettlingen", "burgwedel", "wetzlar"),
}


def _parse_date(s: str) -> date | None:
    """DD.MM.YYYY at the start of the string; approximate dates (~...) give None."""
    s = (s or "").strip()
    if not s or not s[0].isdigit():
        return None
    try:
        return datetime.strptime(s[:10], "%d.%m.%Y").date()
    except ValueError:
        return None


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def country_of(location: str) -> str:
    """Best-effort country code from a free-form location; '' when unknown."""
    low = (location or "").lower()
    for code, hints in _COUNTRY_HINTS.items():
        for h in hints:
            # short codes must match as a whole word, not inside e.g. "Kerkrade"
            if len(h) <= 2:
                if h in low.replace(",", " ").replace("/", " ").replace("(", " ").replace(")", " ").split():
                    return code
            elif h in low:
                return code
    return ""


def _short(company: str) -> str:
    return html.unescape((company or "").split(" (")[0])


def build_data(rows: list[dict], public: bool) -> dict:
    """Aggregate rows into the JSON the page renders. public=True strips identifying fields."""
    # duplicates are marked in Позиция and must not count
    rows = [r for r in rows if not (r.get("Позиция") or "").startswith("DUPLICATE")]
    n = len(rows)
    st = Counter(r.get("Статус", "") for r in rows)

    applied = sum(st[k] for k in APPLIED)
    replied = sum(st[k] for k in REPLIED)
    funnel = [
        {"label": "Вакансий разобрано",  "count": n},
        {"label": "Прошли отсев",        "count": n - st["отклонена"]},
        {"label": "Откликов отправлено", "count": applied},
        {"label": "Получили ответ",      "count": replied},
        {"label": "Диалог или интервью", "count": st["в переписке"] + st["интервью"]},
        {"label": "Интервью",            "count": st["интервью"]},
        {"label": "Оффер",               "count": 0},
    ]

    status = [{"label": STATUS_LABELS.get(k, k), "count": v} for k, v in st.most_common()]

    dates = [d for d in (_parse_date(r.get("Дата", "")) for r in rows) if d]
    weekly = []
    if dates:
        per_week = Counter(_monday(d) for d in dates)
        w, last = _monday(min(dates)), _monday(max(dates))
        while w <= last:
            weekly.append({"label": w.strftime("%d.%m"), "week": w.isoformat(), "count": per_week.get(w, 0)})
            w += timedelta(days=7)

    rejected_lang = Counter(r.get("Язык (требование)", "") for r in rows if r.get("Статус") == "отклонена")
    lang = [{"label": LANG_LABELS.get(k, k), "count": v} for k, v in rejected_lang.most_common()]

    lv = {k: [0, 0, 0] for k in LEVELS}
    for r in rows:
        k = r.get("Уровень роли", "")
        k = k if k in lv else "Прочее"
        lv[k][0] += 1
        if r.get("Статус") in REPLIED:
            lv[k][1] += 1
        if r.get("Статус") == "затухла":
            lv[k][2] += 1
    roles = [{"label": k, "total": a, "responded": b, "silent": c} for k, (a, b, c) in lv.items()]

    open_rows = []
    for r in rows:
        if r.get("Статус") not in OPEN:
            continue
        d = _parse_date(r.get("Дата", ""))
        tier = r.get("Тип работодателя", "")
        country = country_of(r.get("Локация", ""))
        item = {
            "date": d.isoformat() if d else "",
            "week": _monday(d).isoformat() if d else "",
            "tier": tier,
            "lang": r.get("Язык (требование)", ""),
            "level": r.get("Уровень роли", ""),
            "status": r.get("Статус", ""),
            "match": r.get("Оценка матча", ""),
        }
        if public:
            item["company"] = f"Tier {tier}" + (f", {country}" if country else "")
            item["position"] = item["level"] or "—"
            item["location"] = country or "—"
        else:
            item["company"] = _short(r.get("Компания", ""))
            item["position"] = html.unescape(r.get("Позиция", ""))
            item["location"] = r.get("Локация", "")
            item["note"] = r.get("Вывод / причина", "")
            item["cv"] = r.get("Версия CV", "")
        open_rows.append(item)
    open_rows.sort(key=lambda o: o["date"], reverse=True)

    return {
        "meta": {"public": public, "total": n, "generated": date.today().strftime("%d.%m.%Y")},
        "funnel": funnel, "status": status, "weekly": weekly,
        "lang": lang, "roles": roles, "open": open_rows,
    }


def render_html(data: dict) -> str:
    # "</" inside inline JSON would close the <script> tag early
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (_TEMPLATE
            .replace("__D3_URL__", D3_URL)
            .replace("__D3_SRI__", D3_SRI)
            .replace("__DATA__", payload))


_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Воронка поиска работы</title>
<style>
:root { --bg:#fafaf8; --fg:#1f2328; --muted:#6b7280; --card:#fff; --line:#e5e7eb; --bar:#3b6ea5; --bar2:#9db8d6; --warn:#c2603a; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#16181d; --fg:#e6e8eb; --muted:#9aa3ad; --card:#1e2128; --line:#2f343d; --bar:#6aa0d8; --bar2:#3d5775; --warn:#e08a63; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:960px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:24px; margin:0 0 4px; }
.sub { color:var(--muted); margin:0 0 24px; }
section { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; margin-bottom:16px; }
h2 { font-size:16px; margin:0 0 4px; }
.hint { color:var(--muted); font-size:13px; margin:0 0 12px; }
svg { width:100%; height:auto; display:block; font-size:13px; }
svg text { fill:var(--fg); }
svg .muted, .axis text { fill:var(--muted); }
.axis path, .axis line { stroke:var(--line); }
.bar { fill:var(--bar); }
.bar2 { fill:var(--bar2); }
.warn { fill:var(--warn); }
.filters { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:12px; }
.filters label { font-size:13px; color:var(--muted); }
select { margin-left:6px; padding:4px 6px; background:var(--card); color:var(--fg); border:1px solid var(--line); border-radius:6px; }
.wrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:13px; }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:600; white-space:nowrap; }
.empty { color:var(--muted); padding:12px 0; }
</style>
</head>
<body>
<main>
  <h1>Воронка поиска работы</h1>
  <p class="sub" id="sub"></p>
  <section><h2>Воронка</h2><p class="hint">Доля считается от всех разобранных вакансий.</p><div id="funnel"></div></section>
  <section><h2>Статусы</h2><div id="status"></div></section>
  <section><h2>Вакансии по неделям</h2><p class="hint">Неделя начинается с понедельника.</p><div id="weekly"></div></section>
  <section><h2>Язык в отсеве</h2><p class="hint">Требование к языку у вакансий, отсеянных до отклика.</p><div id="lang"></div></section>
  <section><h2>Ответы по уровню роли</h2><p class="hint">Тёмная часть полосы: получили ответ (переписка, интервью, отказ). В подписи: сколько затухли.</p><div id="roles"></div></section>
  <section>
    <h2>Незакрытые вакансии</h2>
    <p class="hint">Новые, к отклику, отложенные по языку и ожидающие ответа.</p>
    <div class="filters">
      <label>Статус <select id="f-status"></select></label>
      <label>Неделя <select id="f-week"></select></label>
    </div>
    <div class="wrap" id="table"></div>
  </section>
</main>
<script src="__D3_URL__" integrity="__D3_SRI__" crossorigin="anonymous"></script>
<script type="application/json" id="data">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const ALL = 'Все';

document.getElementById('sub').textContent =
  `Вакансий в учёте: ${D.meta.total}. Обновлено ${D.meta.generated}.` + (D.meta.public ? ' Публичная версия: компании обезличены.' : '');

function hbars(sel, items, fmt) {
  const el = d3.select(sel);
  if (!items.length) { el.append('p').attr('class', 'empty').text('Нет данных'); return; }
  const W = 680, row = 30, L = 250, R = 90, H = items.length * row + 4;
  const svg = el.append('svg').attr('viewBox', `0 0 ${W} ${H}`);
  const x = d3.scaleLinear([0, d3.max(items, d => d.count) || 1], [0, W - L - R]);
  const g = svg.selectAll('g').data(items).join('g').attr('transform', (d, i) => `translate(0,${i * row})`);
  g.append('text').attr('x', L - 8).attr('y', row / 2).attr('text-anchor', 'end').attr('dominant-baseline', 'middle').text(d => d.label);
  g.append('rect').attr('class', 'bar').attr('x', L).attr('y', 4).attr('height', row - 10).attr('rx', 3).attr('width', d => Math.max(x(d.count), 1));
  g.append('text').attr('x', d => L + Math.max(x(d.count), 1) + 6).attr('y', row / 2).attr('dominant-baseline', 'middle').text(fmt || (d => d.count));
}

function weekly(sel, items) {
  const el = d3.select(sel);
  if (!items.length) { el.append('p').attr('class', 'empty').text('Нет данных'); return; }
  const W = 640, H = 220, m = {t: 10, r: 10, b: 30, l: 32};
  const svg = el.append('svg').attr('viewBox', `0 0 ${W} ${H}`);
  const x = d3.scaleBand(items.map(d => d.label), [m.l, W - m.r]).padding(0.2);
  const y = d3.scaleLinear([0, d3.max(items, d => d.count) || 1], [H - m.b, m.t]).nice();
  const step = Math.ceil(items.length / 12);
  svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).tickValues(x.domain().filter((_, i) => i % step === 0)).tickSizeOuter(0));
  svg.append('g').attr('class', 'axis').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5));
  svg.selectAll('rect').data(items).join('rect').attr('class', 'bar')
    .attr('x', d => x(d.label)).attr('width', x.bandwidth())
    .attr('y', d => y(d.count)).attr('height', d => y(0) - y(d.count)).attr('rx', 2)
    .append('title').text(d => `Неделя с ${d.label}: ${d.count}`);
}

function roles(sel, items) {
  const el = d3.select(sel);
  const W = 640, row = 36, L = 210, R = 190, H = items.length * row + 4;
  const svg = el.append('svg').attr('viewBox', `0 0 ${W} ${H}`);
  const x = d3.scaleLinear([0, d3.max(items, d => d.total) || 1], [0, W - L - R]);
  const g = svg.selectAll('g').data(items).join('g').attr('transform', (d, i) => `translate(0,${i * row})`);
  g.append('text').attr('x', L - 8).attr('y', row / 2).attr('text-anchor', 'end').attr('dominant-baseline', 'middle').text(d => d.label);
  g.append('rect').attr('class', 'bar2').attr('x', L).attr('y', 6).attr('height', row - 14).attr('rx', 3).attr('width', d => Math.max(x(d.total), 1));
  g.append('rect').attr('class', 'bar').attr('x', L).attr('y', 6).attr('height', row - 14).attr('rx', 3).attr('width', d => x(d.responded));
  g.append('text').attr('x', d => L + Math.max(x(d.total), 1) + 6).attr('y', row / 2).attr('dominant-baseline', 'middle')
    .text(d => `${d.responded} из ${d.total}` + (d.total ? ` (${Math.round(100 * d.responded / d.total)}%)` : '') + (d.silent ? `, затухли: ${d.silent}` : ''));
}

hbars('#funnel', D.funnel, d => `${d.count} (${D.meta.total ? Math.round(100 * d.count / D.meta.total) : 0}%)`);
hbars('#status', D.status);
weekly('#weekly', D.weekly);
hbars('#lang', D.lang);
roles('#roles', D.roles);

// open vacancies table
const COLS = D.meta.public
  ? [['date', 'Дата'], ['company', 'Работодатель'], ['position', 'Роль'], ['location', 'Страна'], ['lang', 'Язык'], ['status', 'Статус'], ['match', 'Матч']]
  : [['date', 'Дата'], ['company', 'Компания'], ['position', 'Позиция'], ['location', 'Локация'], ['tier', 'Тип'], ['lang', 'Язык'], ['level', 'Уровень'], ['status', 'Статус'], ['match', 'Матч'], ['note', 'Вывод'], ['cv', 'CV']];

function fill(id, values) {
  const s = document.getElementById(id);
  [ALL, ...values].forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; s.appendChild(o); });
  s.addEventListener('change', renderTable);
}
fill('f-status', [...new Set(D.open.map(o => o.status))].sort());
fill('f-week', [...new Set(D.open.map(o => o.week).filter(Boolean))].sort().reverse());

function renderTable() {
  const fs = document.getElementById('f-status').value, fw = document.getElementById('f-week').value;
  const rows = D.open.filter(o => (fs === ALL || o.status === fs) && (fw === ALL || o.week === fw));
  const box = document.getElementById('table');
  box.textContent = '';
  if (!rows.length) { const p = document.createElement('p'); p.className = 'empty'; p.textContent = 'Ничего не найдено'; box.appendChild(p); return; }
  const t = document.createElement('table');
  const hr = t.createTHead().insertRow();
  COLS.forEach(([, name]) => { const th = document.createElement('th'); th.textContent = name; hr.appendChild(th); });
  const tb = t.createTBody();
  rows.forEach(o => { const tr = tb.insertRow(); COLS.forEach(([k]) => { tr.insertCell().textContent = o[k] || ''; }); });
  box.appendChild(t);
}
renderTable();
</script>
</body>
</html>
"""
