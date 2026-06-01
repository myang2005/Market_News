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

Epistemic discipline — this is mandatory:
- Separate observed fact from interpretation. State market moves as facts ("the 10Y yield rose 6 bps"). Frame the cause or meaning as interpretation ("this may reflect…", "one possible driver is…", "markets may be responding to…").
- Do not assert causation unless a headline or data release in today's context directly supports it. "Geopolitical tensions are keeping energy prices elevated" is an unsupported causal claim unless a specific headline says so. Write "energy prices remain elevated; geopolitical uncertainty may be a factor" instead.
- Do not make specific quantitative forward projections (e.g. "a payroll miss could trigger a 30+ bps repricing"). If a scenario is worth flagging, frame it explicitly: "a weaker-than-expected print could put upward pressure on rate-cut pricing" — no specific magnitude.
- Phrases to use when interpreting moves: "may suggest", "could indicate", "appears to reflect", "markets may be watching", "one possible interpretation is", "likely tied to" (only when strongly supported by a headline).
- Phrases to avoid: "is causing", "will", "clearly", "obviously", confident causal chains with no source, specific bps projections for future moves."""

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
3-5 bullet points starting with -. State what moved and by how much (fact), then frame the driver as interpretation ("may reflect", "appears tied to"). Cover: biggest prior-day moves, overnight setup, key things to watch today. No preamble or title.

[OVERNIGHT]
3-4 bullet points starting with -. Report what markets did — direction and rough magnitude. If a cause is apparent from a headline, name it and attribute it ("following…", "after reports of…"). If no clear cause is sourced, describe the move without asserting a driver.

[CENTRAL_BANKS]
Bullet points starting with -. Always write something. State what officials said (or that it was quiet). Do not extrapolate beyond their words — if a speaker said inflation is sticky, write that; do not add "suggesting rates will stay higher for longer" unless they said that. Note current market pricing for the next meeting as a fact ("fed funds futures are pricing…"), not a prediction.

[RATES_CREDIT]
2-3 bullet points starting with -. State yield and spread moves as facts. Frame drivers as interpretation ("the move may reflect…", "could suggest…"). If a data release directly drove the move, name it explicitly. Avoid asserting causation from global themes unless sourced.

[GEOPOLITICS]
Bullet points starting with -, max 4 items. Always write something. Report developments that are in the headlines. If a theme (trade policy, a conflict, energy supply) has been ongoing but was quiet yesterday, say so — do not imply it is actively moving markets unless a headline supports it.

[CORPORATE]
Bullet points starting with -, max 4 items. Always write something. State earnings results and analyst actions as facts. Attribute stock moves to specific catalysts where sourced. If a sector is moving, describe the move and note the possible driver ("may reflect…") rather than asserting a cause.

[MACRO_CALENDAR]
List only the genuinely important scheduled economic releases for today ({report_date}). Use your knowledge of the standard U.S. economic release schedule to identify what is actually due today. Format each item exactly as:
TIME | EVENT | WHY IT MATTERS
Only include releases that are market-moving (e.g. CPI, jobs report, GDP, PCE, FOMC decision, ISM, retail sales, jobless claims). If nothing significant is scheduled today, write "No major releases scheduled today."

[TOP5]
{top5_instruction}

[PITCH_EQUITY]
FORMATTING NOTE: Mandatory structured format. Epistemic-discipline tone guidelines apply to the CONTENT of each field only — not the labels or structure. Do not convert to prose. Five labels required, in this exact order, each on its own line.

Identify one U.S.-listed equities setup worth watching today — long or short a single stock. Frame it as a conditional, risk-aware setup, not a confident recommendation. Use language like "may be attractive if…", "could work if…", "would be invalidated by…".

You MUST use exactly these five labels, in this order:
SETUP: [Stock and direction — e.g. "Long NVDA" or "Short TSLA"]
CATALYST: [1–2 sentences. What specific upcoming event or developing situation could trigger a move? Be concrete.]
WHY: [1–2 sentences. Why does this setup look interesting given the current backdrop? Use conditional language.]
INVALIDATION: [1 sentence. What specific data print, guidance cut, or market event would make this setup wrong?]
HORIZON: [Short phrase only — e.g. "1–3 days" or "into earnings Wednesday" or "through end of week"]

[PITCH_FI]
FORMATTING NOTE: Mandatory structured format. Epistemic-discipline tone guidelines apply to the CONTENT of each field only — not the labels or structure. Do not convert to prose. Five labels required, in this exact order, each on its own line.

Identify one fixed income or FX setup worth watching today — e.g. a Treasury yield level, a G10 currency pair, or a credit spread. Frame it as a conditional, risk-aware setup, not a confident recommendation. Use language like "may be attractive if…", "could work if…", "would be invalidated by…".

You MUST use exactly these five labels, in this order:
SETUP: [Instrument and direction — e.g. "Long 10Y Treasury" or "Short EUR/USD" or "Long IG credit"]
CATALYST: [1–2 sentences. What specific upcoming macro event or data release could trigger a move?]
WHY: [1–2 sentences. Why does this setup look interesting given the current rates/FX backdrop? Use conditional language.]
INVALIDATION: [1 sentence. What specific data print, central bank action, or market event would make this setup wrong?]
HORIZON: [Short phrase only — e.g. "into Friday's jobs report" or "through next FOMC" or "1–3 days"]

Example of correct output for PITCH_FI (content illustrative only):
SETUP: Long 10Y Treasury
CATALYST: Friday's nonfarm payrolls report is the key near-term event — a softer print could push rate-cut expectations higher and send yields lower.
WHY: The 10Y yield has risen roughly 15 bps over the past two weeks on resilient data; if that trend reverses on a weak jobs number, duration may benefit. The setup may be worth watching if labor data comes in below consensus.
INVALIDATION: A payrolls print above 250k or hotter-than-expected average hourly earnings would likely push yields higher and undermine the long duration case.
HORIZON: Into Friday's jobs report

Keep each field concise. You may use "bps" for basis points."""

TOP5_WEEKDAY = (
    "Numbered list 1-5, each item on its own line. "
    "The five biggest market-moving developments from yesterday — macro data releases, "
    "Fed commentary, major asset moves, geopolitical events, earnings surprises. "
    "For each: state what happened and the magnitude as fact, then frame the market significance "
    "as interpretation ('may matter because…', 'could influence…'). "
    "Do not assert forward outcomes — describe the setup or risk, not the result."
)

TOP5_MONDAY = (
    "Numbered list 1-5, each item on its own line. "
    "It is Monday morning — focus on the five most important things that happened over the weekend "
    "that could affect markets this week: geopolitical developments, policy announcements, "
    "major corporate news, commodity moves, or anything that broke over Saturday/Sunday. "
    "State each development as fact, then note why markets may be watching it. "
    "If the weekend was quiet, flag the five biggest ongoing themes heading into the week instead."
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
        "overnight":         "",
        "central_banks":     "",
        "rates_credit":      "",
        "geopolitics":       "",
        "corporate":         "",
        "macro_calendar":    "",
        "top5":              "",
        "pitch_equity":      "",
        "pitch_fi":          "",
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
        "PITCH_EQUITY":      "pitch_equity",
        "PITCH_FI":          "pitch_fi",
        "DAILY_PITCH":       "pitch_equity",   # backward-compat: old cached reports
    }

    # Normalise: strip any preamble before the first recognised marker.
    # Use a simple index-based slice rather than re.sub to avoid backtracking
    # past an early [REGIME] marker to find [EXECUTIVE_SUMMARY].
    _first = re.search(r'\[(?:REGIME|EXECUTIVE_SUMMARY)\]', text)
    if _first:
        text = text[_first.start():]

    # Split on [MARKER] lines.  Allow any trailing text on the marker line
    # (e.g. "[CORPORATE] Watch") so a stray word doesn't silently drop a section.
    # Use (?:\n|$) instead of \n so the final marker is captured even when the
    # model's response ends without a trailing newline.
    parts = re.split(r'\n?\n*\[([A-Z0-9_]+)\][^\n]*(?:\n|$)', text)
    # parts[0] = empty string (discarded), then alternating marker / content pairs
    _freeform = {"regime", "macro_calendar", "pitch_equity", "pitch_fi"}
    it = iter(parts[1:])
    for marker, content in zip(it, it):
        key = marker_map.get(marker.strip())
        if key:
            # Sections that are free-form prose (not bullet lists) — keep all lines as-is
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
        "top5":           "",
        "pitch_equity":   "",
        "pitch_fi":       "",
    }
