"""AI-powered market summary using Anthropic Claude."""

import os
import anthropic
from datetime import date


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
        for h in headlines[:15]:
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
1. Your response MUST start with [EXECUTIVE_SUMMARY] — no title, no date, no preamble, no header, nothing before it.
2. Each section marker must be on its own line exactly as written (e.g. [OVERNIGHT], [TOP5]).
3. Do NOT number the sections or add any text on the same line as a marker.

[EXECUTIVE_SUMMARY]
3-5 bullet points starting with -. Cover: biggest prior-day moves and drivers, overnight setup, what to watch today. No preamble or title.

[OVERNIGHT]
3-4 bullet points starting with -. Cover: Asian equity performance, European equity performance, U.S. futures direction, Treasury yield moves, oil and dollar. Be directional and specific.

[CENTRAL_BANKS]
Bullet points starting with -. Write "Nothing notable." if nothing significant occurred.

[RATES_CREDIT]
2-3 bullet points starting with -. Yield curve, spread moves, Treasury auctions, drivers of rate moves.

[GEOPOLITICS]
Bullet points starting with -, max 4 items. Only include developments that are market-relevant.

[CORPORATE]
Bullet points starting with -, max 4 items. Key earnings, notable moves, upgrades/downgrades, M&A.

[TOP5]
{top5_instruction}

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
    prompt = SUMMARY_PROMPT_TEMPLATE.format(context=context, top5_instruction=top5_instruction)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
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
        "executive_summary": "",
        "overnight": "",
        "central_banks": "",
        "rates_credit": "",
        "geopolitics": "",
        "corporate": "",
        "top5": "",
    }

    marker_map = {
        "EXECUTIVE_SUMMARY": "executive_summary",
        "OVERNIGHT":         "overnight",
        "CENTRAL_BANKS":     "central_banks",
        "RATES_CREDIT":      "rates_credit",
        "GEOPOLITICS":       "geopolitics",
        "CORPORATE":         "corporate",
        "TOP5":              "top5",
    }

    # Normalise: ensure the first marker is at the start of a line
    # (handles any preamble Claude sneaks in before [EXECUTIVE_SUMMARY])
    text = re.sub(r'^.*?(?=\[EXECUTIVE_SUMMARY\])', '', text, flags=re.DOTALL)

    # Split on [MARKER] lines — \n+ handles blank lines between sections;
    # the leading \n? handles the very first marker which may be at position 0
    parts = re.split(r'\n?\n*\[([A-Z0-9_]+)\]\s*\n', text)
    # parts[0] = empty string (discarded), then alternating marker / content pairs
    it = iter(parts[1:])
    for marker, content in zip(it, it):
        key = marker_map.get(marker.strip())
        if key:
            # Strip any stray header/title lines that aren't bullet points or numbers
            cleaned = "\n".join(
                line for line in content.splitlines()
                if line.strip().startswith(("-", "•", "*")) or
                   re.match(r'^\d+\.', line.strip()) or
                   not line.strip() or
                   key not in ("executive_summary",)
            )
            sections[key] = cleaned.strip()

    # Fallback: if nothing matched, dump full text into executive_summary
    if not any(sections.values()):
        sections["executive_summary"] = text.strip()

    return sections


def _fallback_summary() -> dict:
    return {
        "executive_summary": "_AI summary unavailable — set ANTHROPIC_API_KEY in .env_",
        "overnight": "",
        "central_banks": "",
        "rates_credit": "",
        "geopolitics": "",
        "corporate": "",
        "top5": "",
    }
