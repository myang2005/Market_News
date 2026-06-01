"""AI-powered market summary using Anthropic Claude."""

import os
import anthropic
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)


def build_market_context(prices: dict, headlines: list[dict], report_date: date, prior_day: date) -> str:
    """Build a structured text blob describing the market for Claude."""
    lines = [f"Report date: {report_date}  |  Prior trading day: {prior_day}\n"]

    lines.append("=== PRIOR-DAY MARKET DATA ===")
    for name, d in prices.items():
        pct = d.get("pct_change", 0)
        close = d.get("close", 0)
        chg = d.get("change", 0)
        sign = "+" if chg >= 0 else ""
        lines.append(f"{name}: {close:.4g}  ({sign}{chg:.4g}, {sign}{pct:.2f}%)")

    if headlines:
        lines.append("\n=== TOP MARKET HEADLINES ===")
        for h in headlines[:10]:
            lines.append(f"- [{h['source']}] {h['title']}")
            if h.get("description"):
                lines.append(f"  {h['description'][:120]}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are writing a daily morning markets briefing for someone who is relatively new to the finance industry but is actively learning.

Tone guidelines:
- Be clear and direct. Explain what happened and why it matters in plain terms.
- Use standard financial terms (yield curve, basis points, futures, spread) but briefly clarify them when the context helps — e.g. "Treasury yields fell, meaning bond prices rose" or "the VIX (a measure of expected volatility) dropped."
- Do NOT write like a Bloomberg terminal or a Goldman trading desk note. Avoid dense shorthand like "lhs/rhs", "unch", "stops through", "bid-to-cover", "rip", "offered".
- Spell out abbreviations the first time they appear (e.g. "Federal Open Market Committee (FOMC)").
- Keep it concise and informative — not a textbook, not a lecture. One sentence of context is enough.
- If something moved significantly, say why in plain language."""

SUMMARY_PROMPT_TEMPLATE = """Using the market data and headlines below, generate a morning market briefing.

{context}

---

CRITICAL FORMATTING RULES — violating these will break the parser:
1. Your response MUST start with [REGIME] — no title, no date, no preamble, no header, nothing before it.
2. Each section marker must be on its own line exactly as written (e.g. [OVERNIGHT], [TOP5]).
3. Do NOT number the sections or add any text on the same line as a marker.

[REGIME]
A single short phrase (4–8 words) capturing today's overall market regime. Examples: "Tech-led risk-on, rates sticky" / "Risk-off, dollar bid" / "Inflation scare, rates climbing" / "Oil shock, defensives bid" / "Mixed — equities up, bonds down". No bullet points, no period. Just the phrase.

[EXECUTIVE_SUMMARY]
3-5 bullet points starting with -. Cover: biggest prior-day moves and drivers, overnight setup, what to watch today. No preamble or title.

[OVERNIGHT]
3-4 bullet points starting with -. Cover: Asian equity performance, European equity performance, U.S. futures direction, Treasury yield moves, oil and dollar. Be directional and specific.

[CENTRAL_BANKS]
Bullet points starting with -. Always write something — even if it was a quiet day, note the current Fed posture, whether the Fed is in a blackout period, what the market currently expects for the next meeting, or any recent comments worth flagging. Cover Fed, ECB, BOJ, BOE if relevant.

[RATES_CREDIT]
2-3 bullet points starting with -. Yield curve, spread moves, Treasury auctions, drivers of rate moves.

[GEOPOLITICS]
Bullet points starting with -, max 4 items. Always write something — if there were no major developments, briefly note the key ongoing themes (trade policy, conflicts, energy supply) and whether they were quiet or active yesterday.

[CORPORATE]
Bullet points starting with -, max 4 items. Always write something — if earnings were quiet, note what major companies are reporting later this week or what sector themes are driving stocks right now.

[MACRO_CALENDAR]
List only the genuinely important scheduled economic releases for today ({report_date}). Use your knowledge of the standard U.S. economic release schedule to identify what is actually due today. Format each item exactly as:
TIME | EVENT | WHY IT MATTERS
Only include releases that are market-moving (e.g. CPI, jobs report, GDP, PCE, FOMC decision, ISM, retail sales, jobless claims). If nothing significant is scheduled today, write "No major releases scheduled today."

[TOP5]
{top5_instruction}

[DAILY_PITCH]
Pitch one trade idea that is directly supported by the market data and news above. Choose either:
(a) A single U.S.-listed stock — long or short, with a clear catalyst from recent price action or news.
(b) A simple fixed income or FX trade — e.g. long/short a G10 currency pair, long/short a Treasury, or a straightforward investment-grade credit trade. No structured products, no options strategies.

Format your response exactly like this (keep each label on its own line):
TRADE: [e.g. "Long NVDA" or "Short EUR/USD" or "Long 10Y Treasury"]
DIRECTION: [Long or Short]
RATIONALE: [2-4 sentences explaining why — reference the actual data from today's report. What is driving this trade? What is the catalyst or setup? What would make you wrong?]
RISK: [1 sentence on what could go wrong]

Write for someone learning the industry. Avoid jargon. Be direct and specific — no vague statements.

Keep everything concise. You may use "bps" for basis points but avoid heavy trading-desk shorthand. Write for someone smart who is still learning the industry."""

TOP5_WEEKDAY = (
    "Numbered list 1-5, each item on its own line. "
    "The five biggest market-moving developments from yesterday — macro data releases, "
    "Fed commentary, major asset moves, geopolitical events, earnings surprises. "
    "Include the magnitude of the move and why it matters for today's session."
)

TOP5_MONDAY = (
    "Numbered list 1-5, each item on its own line. "
    "It is Monday morning, so focus on the five most important things that happened over the weekend "
    "that could affect markets this week — geopolitical developments, policy announcements, "
    "major corporate news, commodity moves, or anything that broke over Saturday/Sunday. "
    "If the weekend was quiet, flag the five biggest themes heading into the week instead."
)


def generate_summary(prices: dict, headlines: list[dict], report_date: date, prior_day: date, is_monday: bool = False) -> dict:
    """
    Call Claude to generate narrative sections.
    Returns dict with keys: executive_summary, overnight, central_banks,
    rates_credit, geopolitics, corporate, top5.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _fallback_summary()

    client = anthropic.Anthropic(api_key=api_key)
    context = build_market_context(prices, headlines, report_date, prior_day)
    top5_instruction = TOP5_MONDAY if is_monday else TOP5_WEEKDAY

    try:
        # Split prompt into static instructions (cacheable) + live market data (not cached).
        # The static section template never changes day-to-day — caching it cuts token
        # costs ~90% on those tokens after the first call.
        static_instructions = SUMMARY_PROMPT_TEMPLATE.format(
            context="<MARKET_DATA_PLACEHOLDER>",
            top5_instruction=top5_instruction,
            report_date=report_date.strftime("%A, %B %d, %Y"),
        ).split("<MARKET_DATA_PLACEHOLDER>")

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2800,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{
                "role": "user",
                "content": [
                    # Static instructions — cached after first call
                    {
                        "type": "text",
                        "text": static_instructions[0],
                        "cache_control": {"type": "ephemeral"},
                    },
                    # Live market data — always fresh, not cached
                    {
                        "type": "text",
                        "text": context,
                    },
                    # Closing instructions — cached
                    {
                        "type": "text",
                        "text": static_instructions[1],
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            }],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        raw = message.content[0].text
        return parse_claude_response(raw)
    except Exception as e:
        print(f"Claude API error: {e}")
        return _fallback_summary()


def parse_claude_response(text: str) -> dict:
    """Parse Claude's response by splitting on explicit [SECTION] markers."""
    import re

    sections = {
        "regime":            "",
        "executive_summary": "",
        "overnight": "",
        "central_banks": "",
        "rates_credit": "",
        "geopolitics": "",
        "corporate": "",
        "macro_calendar": "",
        "top5": "",
        "daily_pitch": "",
    }

    marker_map = {
        "REGIME":            "regime",
        "EXECUTIVE_SUMMARY": "executive_summary",
        "OVERNIGHT":         "overnight",
        "CENTRAL_BANKS":     "central_banks",
        "RATES_CREDIT":      "rates_credit",
        "GEOPOLITICS":       "geopolitics",
        "CORPORATE":         "corporate",
        "MACRO_CALENDAR":    "macro_calendar",
        "TOP5":              "top5",
        "DAILY_PITCH":       "daily_pitch",
    }

    # Normalise: strip any preamble before the first recognised marker.
    # Use a simple index-based slice rather than re.sub to avoid backtracking
    # past an early [REGIME] marker to find [EXECUTIVE_SUMMARY].
    _first = re.search(r'\[(?:REGIME|EXECUTIVE_SUMMARY)\]', text)
    if _first:
        text = text[_first.start():]

    # Split on [MARKER] lines.  Allow any trailing text on the marker line
    # (e.g. "[CORPORATE] Watch") so a stray word doesn't silently drop a section.
    parts = re.split(r'\n?\n*\[([A-Z0-9_]+)\][^\n]*\n', text)
    # parts[0] = empty string (discarded), then alternating marker / content pairs
    it = iter(parts[1:])
    for marker, content in zip(it, it):
        key = marker_map.get(marker.strip())
        if key:
            # Sections that are free-form prose (not bullet lists) — keep all lines as-is
            _freeform = {"regime", "macro_calendar", "daily_pitch"}
            if key in _freeform:
                sections[key] = content.strip()
            else:
                # For bullet sections, strip any stray header/title lines
                cleaned = "\n".join(
                    line for line in content.splitlines()
                    if line.strip().startswith(("-", "•", "*")) or
                       re.match(r'^\d+\.', line.strip()) or
                       not line.strip()
                )
                sections[key] = cleaned.strip()

    # Fallback: if nothing matched, dump full text into executive_summary
    if not any(sections.values()):
        sections["executive_summary"] = text.strip()

    return sections


def _fallback_summary() -> dict:
    return {
        "regime":            "",
        "executive_summary": "_AI summary unavailable — set ANTHROPIC_API_KEY in .env_",
        "overnight": "",
        "central_banks": "",
        "rates_credit": "",
        "geopolitics": "",
        "corporate": "",
        "macro_calendar": "",
        "top5": "",
        "daily_pitch": "",
    }
