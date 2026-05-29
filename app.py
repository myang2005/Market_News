"""Market News Dashboard — Streamlit app."""

import streamlit as st
from datetime import date, timedelta
import pandas as pd
from dotenv import load_dotenv

import market_data
import report_generator

load_dotenv()

st.set_page_config(
    page_title="Market News Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main { background-color: #0e1117; }
  h1, h2, h3 { font-family: "IBM Plex Sans", sans-serif; }
  .metric-green { color: #00c853; font-weight: 700; }
  .metric-red   { color: #ff1744; font-weight: 700; }
  .metric-flat  { color: #90a4ae; font-weight: 700; }
  .section-header {
    background: linear-gradient(90deg, #1a237e 0%, #0d47a1 100%);
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #e3f2fd;
    margin-bottom: 8px;
  }
  .stDataFrame td { font-size: 0.82rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def color_pct(val: float) -> str:
    if val > 0:
        return f'<span class="metric-green">+{val:.2f}%</span>'
    if val < 0:
        return f'<span class="metric-red">{val:.2f}%</span>'
    return f'<span class="metric-flat">0.00%</span>'


def color_chg(chg: float) -> str:
    if chg > 0:
        return f'<span class="metric-green">+{chg:.4g}</span>'
    if chg < 0:
        return f'<span class="metric-red">{chg:.4g}</span>'
    return f'<span class="metric-flat">unch</span>'


def build_price_table(prices: dict, names: list[str]) -> pd.DataFrame:
    rows = []
    for name in names:
        d = prices.get(name)
        if not d:
            continue
        close = d["close"]
        chg = d["change"]
        pct = d["pct_change"]
        rows.append({
            "Market": name,
            "Close": market_data.format_value(name, close),
            "Change": f"+{chg:.4g}" if chg >= 0 else f"{chg:.4g}",
            "% Change": f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%",
        })
    return pd.DataFrame(rows)


def style_dataframe(df: pd.DataFrame):
    def highlight_pct(val):
        if isinstance(val, str) and val.startswith("+"):
            return "color: #00c853; font-weight: bold"
        if isinstance(val, str) and val.startswith("-"):
            return "color: #ff1744; font-weight: bold"
        return ""

    return df.style.applymap(highlight_pct, subset=["% Change", "Change"])


def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def safe_md(text: str) -> str:
    """Escape dollar signs and strip stray markdown bold markers from Claude output."""
    return text.replace("$", r"\$").replace("**", "")


# ── Sidebar: controls ─────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Settings")
    override_date = st.date_input(
        "Report date (default: today)",
        value=date.today(),
        max_value=date.today(),
    )
    refresh = st.button("Refresh / Generate Report")

# ── Session state: cache report ───────────────────────────────────────────────

if "report" not in st.session_state or refresh:
    with st.spinner("Fetching market data and generating AI summary…"):
        st.session_state["report"] = report_generator.generate_report(
            force_date=override_date
        )

report = st.session_state["report"]

# ── Header ────────────────────────────────────────────────────────────────────

col_title, col_date = st.columns([3, 1])
with col_title:
    st.title("📈 Daily Markets Dashboard")
with col_date:
    st.markdown(
        f"<div style='text-align:right; padding-top:16px; color:#1a237e;'>"
        f"{report['report_date'].strftime('%A, %B %d, %Y')}<br>"
        f"<small>Prior close: {report['prior_day'] if report['prior_day'] else 'N/A'}</small>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Market closed notice ──────────────────────────────────────────────────────

if not report["market_open"]:
    st.warning(
        f"The U.S. equity market was **closed** on {report.get('prior_day', 'the prior trading day')}. "
        "No full market update is available."
    )
    st.stop()

prices = report["prices"]
summary = report["summary"]
headlines = report["headlines"]
macro_cal = report["macro_calendar"]
is_monday = report.get("is_monday", False)
week_ahead = report.get("week_ahead", [])

# ── Executive Summary ─────────────────────────────────────────────────────────

section_header("Executive Summary")
exec_text = summary.get("executive_summary", "")
if exec_text:
    for line in exec_text.strip().split("\n"):
        line = line.strip()
        # Skip stray headers, dates, or title lines Claude sometimes prepends
        if not line:
            continue
        if line.startswith("#"):
            continue
        if any(line.upper().startswith(kw) for kw in ("MORNING MARKET", "DAILY MARKET", "MARKET DASHBOARD")):
            continue
        # Strip common bullet prefixes
        line = line.lstrip("•-* ")
        if line:
            st.markdown(f"- {safe_md(line)}")
else:
    st.info("AI summary unavailable — set ANTHROPIC_API_KEY in .env")

st.divider()

# ── Prior-Day Market Snapshot ─────────────────────────────────────────────────

section_header("Prior-Day Market Snapshot")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**U.S. Equities**")
    df_eq = build_price_table(prices, market_data.EQUITY_NAMES)
    if not df_eq.empty:
        st.dataframe(style_dataframe(df_eq), use_container_width=True, hide_index=True)

with c2:
    st.markdown("**International Equities**")
    df_intl = build_price_table(prices, market_data.INTL_NAMES)
    if not df_intl.empty:
        st.dataframe(style_dataframe(df_intl), use_container_width=True, hide_index=True)

st.divider()

# ── Rates & FX & Commodities ──────────────────────────────────────────────────

section_header("Rates, FX & Commodities")

c3, c4, c5 = st.columns(3)

with c3:
    st.markdown("**Rates**")
    df_rates = build_price_table(prices, market_data.RATES_NAMES)
    spread = market_data.get_yield_spread(prices)
    if spread is not None:
        spread_row = pd.DataFrame([{
            "Market": "T-Bill vs 10Y Spread",
            "Close": f"{spread} bps",
            "Change": "—",
            "% Change": "—",
        }])
        df_rates = pd.concat([df_rates, spread_row], ignore_index=True)
    if not df_rates.empty:
        st.dataframe(style_dataframe(df_rates), use_container_width=True, hide_index=True)

with c4:
    st.markdown("**FX**")
    df_fx = build_price_table(prices, market_data.FX_NAMES)
    if not df_fx.empty:
        st.dataframe(style_dataframe(df_fx), use_container_width=True, hide_index=True)

with c5:
    st.markdown("**Commodities & Crypto**")
    df_comm = build_price_table(prices, market_data.COMMODITY_NAMES + market_data.CRYPTO_NAMES)
    if not df_comm.empty:
        st.dataframe(style_dataframe(df_comm), use_container_width=True, hide_index=True)

st.divider()

# ── Overnight + Rates Commentary ─────────────────────────────────────────────

c6, c7 = st.columns(2)

with c6:
    section_header("Overnight Market Update")
    overnight = summary.get("overnight", "")
    if overnight:
        for line in overnight.strip().split("\n"):
            line = line.strip().lstrip("•-* ")
            if line:
                st.markdown(f"- {safe_md(line)}")
    else:
        st.caption("No overnight summary available.")

with c7:
    section_header("Rates & Credit Watch")
    rates_text = summary.get("rates_credit", "")
    if rates_text:
        for line in rates_text.strip().split("\n"):
            line = line.strip().lstrip("•-* ")
            if line:
                st.markdown(f"- {safe_md(line)}")
    else:
        st.caption("No rates commentary available.")

st.divider()

# ── Central Banks + Geopolitics ───────────────────────────────────────────────

c8, c9 = st.columns(2)

with c8:
    section_header("Central Banks")
    cb_text = summary.get("central_banks", "")
    if cb_text and "nothing notable" not in cb_text.lower():
        for line in cb_text.strip().split("\n"):
            line = line.strip().lstrip("•-* ")
            if line:
                st.markdown(f"- {safe_md(line)}")
    else:
        st.caption("Nothing notable from central banks.")

with c9:
    section_header("Geopolitics & Macro Themes")
    geo_text = summary.get("geopolitics", "")
    if geo_text:
        for line in geo_text.strip().split("\n"):
            line = line.strip().lstrip("•-* ")
            if line:
                st.markdown(f"- {safe_md(line)}")
    else:
        st.caption("No notable geopolitical developments.")

st.divider()

# ── Corporate / Earnings Watch ────────────────────────────────────────────────

section_header("Corporate / Earnings Watch")
corp_text = summary.get("corporate", "")
if corp_text:
    for line in corp_text.strip().split("\n"):
        line = line.strip().lstrip("•-* ")
        if line:
            st.markdown(f"- {safe_md(line)}")
else:
    st.caption("No notable corporate events.")

st.divider()

# ── Macro Calendar ────────────────────────────────────────────────────────────

section_header("Today's Macro Calendar")
if macro_cal:
    df_cal = pd.DataFrame(macro_cal)
    st.dataframe(df_cal, use_container_width=True, hide_index=True)
else:
    st.caption("No scheduled macro events found.")

# ── Week Ahead (Mondays only) ────────────────────────────────────────────────

if is_monday and week_ahead:
    st.divider()
    section_header("Week Ahead — Key Events This Week")
    st.caption("It's Monday — here's what to watch for across the trading week.")
    df_week = pd.DataFrame(week_ahead)
    st.dataframe(df_week, use_container_width=True, hide_index=True)

st.divider()

# ── Top 5 ─────────────────────────────────────────────────────────────────────

top5_label = "5 Key Things That Happened This Weekend" if is_monday else "5 Biggest Market-Moving Events Yesterday"
section_header(top5_label)
top5 = summary.get("top5", "")
if top5:
    count = 1
    for line in top5.strip().split("\n"):
        line = line.strip().lstrip("0123456789.-) ")
        if line:
            st.markdown(f"**{count}.** {safe_md(line)}")
            count += 1
else:
    st.caption("No top-5 items generated.")

st.divider()

# ── Raw Headlines ─────────────────────────────────────────────────────────────

with st.expander("Raw Headlines (source data)"):
    if headlines:
        for h in headlines[:20]:
            st.markdown(
                f"**[{h['source']}]** [{h['title']}]({h['url']})  \n"
                f"<small>{h.get('published', '')} — {(h.get('description') or '')[:120]}</small>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No headlines fetched. Add a NEWS_API_KEY to .env for live news.")

# ── Quote of the Day ─────────────────────────────────────────────────────────

QUOTES = [
    ("The stock market is a device for transferring money from the impatient to the patient.", "Warren Buffett"),
    ("In investing, what is comfortable is rarely profitable.", "Robert Arnott"),
    ("The four most dangerous words in investing are: 'This time it's different.'", "Sir John Templeton"),
    ("Risk comes from not knowing what you're doing.", "Warren Buffett"),
    ("The market can stay irrational longer than you can stay solvent.", "John Maynard Keynes"),
    ("It's not whether you're right or wrong, but how much money you make when you're right and how much you lose when you're wrong.", "George Soros"),
    ("In the short run, the market is a voting machine. In the long run, it is a weighing machine.", "Benjamin Graham"),
    ("The goal of a successful trader is to make the best trades. Money is secondary.", "Alexander Elder"),
    ("Investing should be more like watching paint dry or watching grass grow. If you want excitement, take $800 and go to Las Vegas.", "Paul Samuelson"),
    ("The biggest risk is not taking any risk. In a world that is changing quickly, the only strategy that is guaranteed to fail is not taking risks.", "Mark Zuckerberg"),
    ("Price is what you pay. Value is what you get.", "Warren Buffett"),
    ("The most important quality for an investor is temperament, not intellect.", "Warren Buffett"),
    ("Know what you own, and know why you own it.", "Peter Lynch"),
    ("Markets are constantly in a state of uncertainty and flux, and money is made by discounting the obvious and betting on the unexpected.", "George Soros"),
    ("The time of maximum pessimism is the best time to buy, and the time of maximum optimism is the best time to sell.", "Sir John Templeton"),
    ("Financial markets are extremely complex. When you act, thousands of other actors are acting too, often in ways that are directly opposite to what you anticipated.", "George Soros"),
    ("The key to making money in stocks is not to get scared out of them.", "Peter Lynch"),
    ("Compound interest is the eighth wonder of the world. He who understands it, earns it; he who doesn't, pays it.", "Albert Einstein"),
    ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("Wide diversification is only required when investors do not understand what they are doing.", "Warren Buffett"),
    ("The individual investor should act consistently as an investor and not as a speculator.", "Benjamin Graham"),
    ("In investing, there are no certainties, only probabilities.", "Peter Lynch"),
    ("Be fearful when others are greedy and greedy when others are fearful.", "Warren Buffett"),
    ("The real measure of your wealth is how much you'd be worth if you lost all your money.", "Unknown"),
    ("Opportunities come infrequently. When it rains gold, put out the bucket, not the thimble.", "Warren Buffett"),
    ("The secret to investing is to figure out the value of something — and then pay a lot less.", "Joel Greenblatt"),
    ("Volatility is the price you pay for performance.", "Howard Marks"),
    ("Good investing is not about making good decisions. It's about consistently not screwing up.", "Morgan Housel"),
    ("The stock market is filled with individuals who know the price of everything, but the value of nothing.", "Philip Fisher"),
    ("Every portfolio benefits from bonds; they dampen volatility and provide a cushion against the unexpected.", "Pimco"),
]

import hashlib
day_hash = int(hashlib.md5(str(report["report_date"]).encode()).hexdigest(), 16)
quote_text, quote_author = QUOTES[day_hash % len(QUOTES)]

section_header("Quote of the Day")
st.markdown(
    f"<blockquote style='"
    f"border-left: 3px solid #1a237e; "
    f"padding: 12px 20px; "
    f"margin: 8px 0; "
    f"font-style: italic; "
    f"font-size: 1.05rem; "
    f"color: #000000;"
    f"'>"
    f'"{quote_text}"'
    f"<br><br>"
    f"<span style='font-style: normal; font-weight: 600; font-size: 0.9rem; color: #000000;'>"
    f"— {quote_author}"
    f"</span></blockquote>",
    unsafe_allow_html=True,
)

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    "<div style='text-align:center; color:#546e7a; font-size:0.75rem; padding-top:20px;'>"
    "Market News Dashboard &nbsp;|&nbsp; Data: Yahoo Finance &nbsp;|&nbsp; AI: Claude (Anthropic)"
    "</div>",
    unsafe_allow_html=True,
)
