"""Market News Dashboard — Streamlit app."""

import streamlit as st
from datetime import date, timedelta
import pandas as pd
import hashlib
import re as _re
import os
from dotenv import load_dotenv
from pathlib import Path
import plotly.graph_objects as go
import yfinance as yf

# Load .env for local dev
load_dotenv(Path(__file__).parent / ".env", override=True)

# On Streamlit Cloud secrets are in st.secrets — push them into os.environ
# so every module that uses os.getenv() picks them up automatically.
for _secret_key in ["ANTHROPIC_API_KEY", "NEWS_API_KEY"]:
    if not os.environ.get(_secret_key):
        try:
            os.environ[_secret_key] = st.secrets[_secret_key]
        except Exception:
            pass

import market_data
import report_generator


CHART_TICKERS = {
    "S&P 500":            "^GSPC",
    "Nasdaq 100":         "^NDX",
    "10Y Treasury Yield": "^TNX",
    "VIX":                "^VIX",
    "EUR/USD":            "EURUSD=X",
    "Gold":               "GC=F",
    "Brent Crude":        "BZ=F",
}

CHART_COLORS = {
    "S&P 500":            "#1d4ed8",
    "Nasdaq 100":         "#7c3aed",
    "10Y Treasury Yield": "#dc2626",
    "VIX":                "#d97706",
    "EUR/USD":            "#059669",
    "Gold":               "#b7791f",
    "Brent Crude":        "#0891b2",
}


@st.cache_data(ttl=3600)
def fetch_chart_data_daily() -> dict:
    """3 months of daily closes for all chart tickers. Cached 1 hr."""
    end   = date.today()
    start = end - timedelta(days=100)
    raw = yf.download(
        list(CHART_TICKERS.values()),
        start=str(start), end=str(end),
        auto_adjust=True, progress=False, threads=True,
    )
    closes = raw["Close"] if "Close" in raw else raw
    result = {}
    for name, sym in CHART_TICKERS.items():
        if sym in closes.columns:
            s = closes[sym].dropna()
            if not s.empty:
                result[name] = s
    return result


@st.cache_data(ttl=1800)
def fetch_chart_data_5d() -> dict:
    """5 days of hourly data for all chart tickers. Cached 30 min."""
    raw = yf.download(
        list(CHART_TICKERS.values()),
        period="5d", interval="1h",
        auto_adjust=True, progress=False, threads=True,
    )
    closes = raw["Close"] if "Close" in raw else raw
    result = {}
    for name, sym in CHART_TICKERS.items():
        if sym in closes.columns:
            s = closes[sym].dropna()
            if not s.empty:
                result[name] = s
    return result


st.set_page_config(
    page_title="Market News Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Palette & base ── */
  :root {
    --bg:     #f6f8fc;
    --card:   #ffffff;
    --navy:   #102a73;
    --blue:   #1d4ed8;
    --text:   #1f2937;
    --muted:  #6b7280;
    --border: #e5e7eb;
    --green:  #059669;
    --red:    #dc2626;
    --gold:   #b7791f;
  }

  /* Page background */
  [data-testid="stAppViewContainer"] > .main,
  [data-testid="stAppViewContainer"] {
    background-color: #f6f8fc !important;
  }
  [data-testid="stSidebar"] { background-color: #ffffff; }

  /* Typography */
  html, body, [class*="css"] {
    font-family: Inter, "Helvetica Neue", Arial, sans-serif;
    color: #1f2937;
  }

  /* ── Section label headers (thin border-left style) ── */
  .section-label {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #102a73;
    border-left: 4px solid #102a73;
    padding-left: 10px;
    margin: 0 0 14px 0;
    line-height: 1.4;
  }

  /* ── Section spacing ── */
  .section-block { margin-bottom: 32px; }

  /* ── Key-takeaway tiles (executive summary) ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
  }
  .kpi-tile {
    background: #f0f4ff;
    border: 1px solid #dde5f7;
    border-radius: 10px;
    padding: 12px 14px;
    text-align: center;
  }
  .kpi-name  { font-size: 0.72rem; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.06em; }
  .kpi-value { font-size: 1.15rem; font-weight: 700; color: #102a73; margin: 4px 0 2px; }
  .kpi-note  { font-size: 0.68rem; color: #6b7280; }
  .kpi-pos   { color: #059669 !important; }
  .kpi-neg   { color: #dc2626 !important; }

  /* ── Status chips ── */
  .chip {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.70rem;
    font-weight: 700;
    background: #eef2ff;
    color: #102a73;
    margin: 0 4px 6px 0;
    letter-spacing: 0.04em;
  }
  .chip-red    { background: #fee2e2; color: #dc2626; }
  .chip-green  { background: #d1fae5; color: #059669; }
  .chip-gold   { background: #fef3c7; color: #b7791f; }
  .chip-gray   { background: #f3f4f6; color: #6b7280; }

  /* ── Bullet sections ── */
  ul { margin: 0; padding-left: 1.2rem; }
  li { margin-bottom: 10px; line-height: 1.6; }

  /* ── Tables ── */
  .stDataFrame { border-radius: 10px; overflow: hidden; }
  .stDataFrame td  { font-size: 0.88rem; padding: 10px 14px !important; }
  .stDataFrame th  { font-size: 0.78rem; color: #6b7280; font-weight: 600; background: #f8fafc !important; padding: 10px 14px !important; }

  /* Positive / negative in tables */
  .pos { color: #059669; font-weight: 700; }
  .neg { color: #dc2626; font-weight: 700; }

  /* Remove default Streamlit divider heaviness */
  hr { border-color: #e5e7eb !important; margin: 18px 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────


def section_label(title: str):
    st.markdown(f'<p class="section-label">{title}</p>', unsafe_allow_html=True)

def safe_md(text: str) -> str:
    return text.replace("$", r"\$").replace("**", "")

def render_bullets(text: str):
    for line in text.strip().split("\n"):
        line = line.strip().lstrip("•-* ")
        if line:
            st.markdown(f"- {safe_md(line)}")

def build_price_table(prices: dict, names: list) -> pd.DataFrame:
    rows = []
    for name in names:
        d = prices.get(name)
        if not d:
            continue
        close = d["close"]
        chg   = d["change"]
        pct   = d["pct_change"]
        rows.append({
            "Market":   name,
            "Close":    market_data.format_value(name, close),
            "Change":   f"+{chg:.4g}" if chg >= 0 else f"{chg:.4g}",
            "% Change": f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%",
        })
    return pd.DataFrame(rows)

def style_df(df: pd.DataFrame):
    def hl(val):
        if isinstance(val, str) and val.startswith("+"):
            return "color: #059669; font-weight: 700"
        if isinstance(val, str) and val.startswith("-"):
            return "color: #dc2626; font-weight: 700"
        return ""
    return df.style.map(hl, subset=["% Change", "Change"])


# ── Sidebar ───────────────────────────────────────────────────────────────────

if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = date.today()
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

with st.sidebar:
    st.title("Settings")

    if st.button("Today's Report", width='stretch'):
        st.session_state["selected_date"] = date.today()
        st.session_state.pop("report", None)

    # Past reports dropdown
    _reports_dir = Path(__file__).parent / "reports"
    _past = sorted(
        [
            date.fromisoformat(p.stem)
            for p in _reports_dir.glob("*.json")
            if p.stem != str(date.today())
        ],
        reverse=True,
    )[:15]

    if _past:
        with st.expander("Past Reports"):
            for _d in _past:
                _label = _d.strftime("%A, %b %d")
                if _d == st.session_state["selected_date"]:
                    _label = f"● {_label}"
                if st.button(_label, key=f"hist_{_d}", width='stretch'):
                    st.session_state["selected_date"] = _d
                    st.session_state.pop("report", None)

    if st.button("Charts", width='stretch'):
        st.session_state["page"] = "charts"

    st.divider()
    force_refresh = st.button("Force Regenerate", help="Discard cache and call APIs again (uses credits)")

override_date = st.session_state["selected_date"]

# ── Load report ───────────────────────────────────────────────────────────────

# ── Charts page ───────────────────────────────────────────────────────────────

if st.session_state["page"] == "charts":
    if st.button("← Back to Dashboard"):
        st.session_state["page"] = "dashboard"
        st.rerun()

    st.markdown(
        "<div style='font-size:2.2rem; font-weight:750; letter-spacing:-0.03em;"
        "color:#102a73; padding: 28px 0 4px;'>Market Charts</div>"
        "<div style='font-size:0.92rem; color:#6b7280; margin-bottom:24px;'>"
        "5D · 1M · 3M &nbsp;·&nbsp; Data via Yahoo Finance &nbsp;·&nbsp; Refreshed hourly</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Loading chart data…"):
        _daily = fetch_chart_data_daily()
        _5d    = fetch_chart_data_5d()

    # (label, data_source, calendar days to slice; None = use full series)
    PERIODS = [
        ("5D",  _5d,   None),
        ("1M",  _daily, 35),
        ("3M",  _daily, 100),
    ]

    def _make_chart(series, period_label, color):
        pct_chg = (series.iloc[-1] / series.iloc[0] - 1) * 100
        sign = "+" if pct_chg >= 0 else ""
        chg_color = "#059669" if pct_chg >= 0 else "#dc2626"
        fmt = "%b %d %H:%M" if period_label == "5D" else "%b %d"
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            mode="lines",
            line=dict(color=color, width=2),
            hovertemplate=f"%{{x|{fmt}}}<br>%{{y:.4g}}<extra></extra>",
        ))
        fig.update_layout(
            title=dict(
                text=f"<b>{period_label}</b>&nbsp;&nbsp;"
                     f"<span style='font-size:12px; color:{chg_color}'>"
                     f"{sign}{pct_chg:.2f}%</span>",
                font=dict(size=14, color="#102a73"),
                x=0, xanchor="left",
            ),
            margin=dict(l=8, r=8, t=44, b=8),
            height=210,
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            xaxis=dict(showgrid=False, tickformat=fmt, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9)),
            showlegend=False,
        )
        return fig

    for name in CHART_TICKERS:
        section_label(name)
        cols = st.columns(3)
        color = CHART_COLORS.get(name, "#102a73")

        for col, (period_label, source, days) in zip(cols, PERIODS):
            with col:
                full = source.get(name)
                if full is None or full.empty:
                    st.caption("No data")
                    continue
                if days is not None:
                    cutoff = pd.Timestamp.now()
                    if full.index.tz is not None:
                        cutoff = cutoff.tz_localize(full.index.tz)
                    series = full[full.index >= cutoff - pd.Timedelta(days=days)]
                else:
                    series = full
                if series.empty or len(series) < 2:
                    st.caption("No data")
                    continue
                st.plotly_chart(
                    _make_chart(series, period_label, color),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
        st.divider()

    st.stop()

# ── Load report ───────────────────────────────────────────────────────────────

# Reload when the selected date changes
if st.session_state.get("loaded_date") != override_date:
    st.session_state.pop("report", None)

if force_refresh:
    cache_path = Path(__file__).parent / "reports" / f"{override_date}.json"
    if cache_path.exists():
        cache_path.unlink()
    st.session_state.pop("report", None)

if "report" not in st.session_state:
    with st.spinner("Loading report…"):
        st.session_state["report"] = report_generator.generate_report(force_date=override_date)
        st.session_state["loaded_date"] = override_date

report  = st.session_state["report"]

# ── Header ────────────────────────────────────────────────────────────────────

def _regime_badge(regime: str) -> str:
    """Return an HTML pill badge colored by sentiment keyword."""
    if not regime:
        return ""
    low = regime.lower()
    if any(w in low for w in ("risk-on", "risk on", "rally", "bullish", "led rally", "led risk")):
        bg, fg = "#d1fae5", "#065f46"
    elif any(w in low for w in ("risk-off", "risk off", "selloff", "bearish", "shock", "scare",
                                 "flight to safety", "defensives")):
        bg, fg = "#fee2e2", "#991b1b"
    elif any(w in low for w in ("mixed", "cautious", "uncertain", "sticky", "inflation")):
        bg, fg = "#fef3c7", "#92400e"
    else:
        bg, fg = "#e0e7ff", "#3730a3"
    return (
        f"<span style='display:inline-block; background:{bg}; color:{fg}; "
        f"padding:3px 12px; border-radius:999px; font-size:0.75rem; "
        f"font-weight:700; letter-spacing:0.05em; text-transform:uppercase; "
        f"margin-top:8px;'>REGIME: {regime}</span>"
    )

_regime_text = report.get("summary", {}).get("regime", "")
_badge_html  = _regime_badge(_regime_text)

st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end;
                padding: 28px 0 20px;">
      <div>
        <div style="font-size:2.2rem; font-weight:750; letter-spacing:-0.03em;
                    color:#102a73; line-height:1.1;">
          Daily Markets Dashboard
        </div>
        <div style="font-size:0.92rem; color:#6b7280; margin-top:4px;">
          Market briefing &nbsp;·&nbsp;
          {report['report_date'].strftime('%A, %B %d, %Y')}
          &nbsp;·&nbsp; Prior close: {report['prior_day'] if report['prior_day'] else 'N/A'}
        </div>
        {_badge_html}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Market closed notice ──────────────────────────────────────────────────────

if not report["market_open"]:
    st.warning(
        f"The U.S. equity market was **closed** on "
        f"{report.get('prior_day', 'the prior trading day')}. "
        "No full market update is available."
    )
    st.stop()

prices            = report["prices"]
summary           = report["summary"]
headlines         = report["headlines"]
is_monday         = report.get("is_monday", False)
week_ahead        = report.get("week_ahead", [])
earnings_today    = report.get("earnings_today", [])
earnings_this_week= report.get("earnings_this_week", [])
scraped_calendar  = report.get("macro_calendar", [])

# ── Executive Summary ─────────────────────────────────────────────────────────

section_label("Executive Summary")

kpi_names  = ["S&P 500", "10Y Treasury", "VIX"]
kpi_labels = {"S&P 500": "S&P 500", "10Y Treasury": "10Y Yield", "VIX": "VIX"}
kpi_html   = '<div class="kpi-grid">'
for kn in kpi_names:
    d = prices.get(kn, {})
    if d:
        val_str = market_data.format_value(kn, d["close"])
        pct     = d["pct_change"]
        pct_cls = "kpi-pos" if pct >= 0 else "kpi-neg"
        pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
        kpi_html += (
            f'<div class="kpi-tile">'
            f'<div class="kpi-name">{kpi_labels[kn]}</div>'
            f'<div class="kpi-value {pct_cls}">{val_str}</div>'
            f'<div class="kpi-note {pct_cls}">{pct_str}</div>'
            f'</div>'
        )
kpi_html += '</div>'
st.markdown(kpi_html, unsafe_allow_html=True)

exec_text = summary.get("executive_summary", "")
if exec_text:
    for line in exec_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if any(line.upper().startswith(kw) for kw in ("MORNING MARKET", "DAILY MARKET", "MARKET DASHBOARD")):
            continue
        line = line.lstrip("•-* ")
        if line:
            st.markdown(f"- {safe_md(line)}")
else:
    st.info("AI summary unavailable — set ANTHROPIC_API_KEY in .env")

st.divider()

# ── Prior-Day Market Snapshot ─────────────────────────────────────────────────

section_label("Prior-Day Market Snapshot")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**U.S. Equities**")
    df_eq = build_price_table(prices, market_data.EQUITY_NAMES)
    if not df_eq.empty:
        st.dataframe(style_df(df_eq), hide_index=True)

with c2:
    st.markdown("**International Equities**")
    df_intl = build_price_table(prices, market_data.INTL_NAMES)
    if not df_intl.empty:
        st.dataframe(style_df(df_intl), hide_index=True)

st.divider()

# ── Rates, FX & Commodities ───────────────────────────────────────────────────

section_label("Rates, FX & Commodities")

c3, c4, c5 = st.columns(3)

with c3:
    st.markdown("**Rates**")
    df_rates = build_price_table(prices, market_data.RATES_NAMES)
    spread = market_data.get_yield_spread(prices)
    if spread is not None:
        df_rates = pd.concat([df_rates, pd.DataFrame([{
            "Market": "T-Bill vs 10Y Spread",
            "Close": f"{spread} bps",
            "Change": "—",
            "% Change": "—",
        }])], ignore_index=True)
    if not df_rates.empty:
        st.dataframe(style_df(df_rates), hide_index=True)

with c4:
    st.markdown("**FX**")
    df_fx = build_price_table(prices, market_data.FX_NAMES)
    if not df_fx.empty:
        st.dataframe(style_df(df_fx), hide_index=True)

with c5:
    st.markdown("**Commodities & Crypto**")
    df_comm = build_price_table(prices, market_data.COMMODITY_NAMES + market_data.CRYPTO_NAMES)
    if not df_comm.empty:
        st.dataframe(style_df(df_comm), hide_index=True)

st.divider()

# ── Overnight + Rates & Credit ────────────────────────────────────────────────

c6, c7 = st.columns(2)

with c6:
    section_label("Overnight Market Update")
    overnight = summary.get("overnight", "")
    if overnight:
        render_bullets(overnight)
    else:
        st.caption("No overnight summary available.")

with c7:
    section_label("Rates & Credit Watch")
    rates_text = summary.get("rates_credit", "")
    if rates_text:
        render_bullets(rates_text)
    else:
        st.caption("No rates commentary available.")

st.divider()

# ── Central Banks + Geopolitics ───────────────────────────────────────────────

c8, c9 = st.columns(2)

with c8:
    section_label("Central Banks")
    render_bullets(summary.get("central_banks", ""))

with c9:
    section_label("Geopolitics & Macro Themes")
    render_bullets(summary.get("geopolitics", ""))

st.divider()

# ── Corporate / Earnings Watch ────────────────────────────────────────────────

section_label("Corporate / Earnings Watch")
render_bullets(summary.get("corporate", ""))

st.divider()

# ── Today's Economic Calendar ─────────────────────────────────────────────────

section_label("Today's Economic Calendar")

<<<<<<< HEAD
_CAL_COLS      = ["time (ET)", "event", "importance", "note", "previous"]
_CAL_IS_STUB   = (
    len(scraped_calendar) == 1
    and "unavailable" in scraped_calendar[0].get("event", "").lower()
)

if scraped_calendar and not _CAL_IS_STUB:
    _cal_df = pd.DataFrame(scraped_calendar)
    _cal_df = _cal_df[[c for c in _CAL_COLS if c in _cal_df.columns]]
    st.dataframe(_cal_df, hide_index=True)
else:
    # Fall back to AI-inferred calendar text
=======
# Prefer the live scraped calendar; fall back to the AI-generated text table
_cal_is_stub = (
    len(scraped_calendar) == 1
    and "unavailable" in scraped_calendar[0].get("event", "").lower()
)
if scraped_calendar and not _cal_is_stub:
    display_cols = ["time (ET)", "event", "period", "actual", "forecast", "previous", "importance"]
    cal_df = pd.DataFrame(scraped_calendar)[[c for c in display_cols if c in pd.DataFrame(scraped_calendar).columns]]
    st.dataframe(cal_df, hide_index=True)
else:
    # Fall back to AI-inferred calendar
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2
    ai_calendar = summary.get("macro_calendar", "")
    if ai_calendar and "no major releases" not in ai_calendar.lower():
        cal_rows = []
        for line in ai_calendar.strip().split("\n"):
            line = line.strip().lstrip("•-* ")
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
<<<<<<< HEAD
                cal_rows.append({"Time": parts[0], "Event": parts[1], "Note": parts[2]})
            elif len(parts) == 2:
                cal_rows.append({"Time": parts[0], "Event": parts[1], "Note": ""})
            else:
                cal_rows.append({"Time": "—", "Event": line, "Note": ""})
=======
                cal_rows.append({"Time": parts[0], "Event": parts[1], "Why It Matters": parts[2]})
            elif len(parts) == 2:
                cal_rows.append({"Time": parts[0], "Event": parts[1], "Why It Matters": ""})
            else:
                cal_rows.append({"Time": "—", "Event": line, "Why It Matters": ""})
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2
        if cal_rows:
            st.dataframe(pd.DataFrame(cal_rows), hide_index=True)
        else:
            st.caption("No major economic releases scheduled today.")
    else:
        st.caption("No major economic releases scheduled today.")

if earnings_today:
    st.divider()
    section_label("Earnings Today — Priority Watchlist")
<<<<<<< HEAD
    _et_df = pd.DataFrame(earnings_today)
    _et_cols = [c for c in ["company", "ticker", "date", "eps_est", "rev_est"] if c in _et_df.columns]
    st.dataframe(_et_df[_et_cols], hide_index=True)

if is_monday:
    st.divider()
    section_label("Key Events Ahead This Week")
    st.caption("High-impact scheduled events for the week ahead.")
    if week_ahead:
        _wa_df = pd.DataFrame(week_ahead)
        _wa_cols = [c for c in ["date", "event", "importance", "note", "previous"] if c in _wa_df.columns]
        st.dataframe(_wa_df[_wa_cols], hide_index=True)
    if earnings_this_week:
        st.markdown("**Priority earnings reporters this week:**")
        _ew_df = pd.DataFrame(earnings_this_week)
        _ew_cols = [c for c in ["company", "ticker", "date", "eps_est", "rev_est"] if c in _ew_df.columns]
        st.dataframe(_ew_df[_ew_cols], hide_index=True)
=======
    st.dataframe(pd.DataFrame(earnings_today), hide_index=True)

if is_monday:
    st.divider()
    section_label("Week Ahead — Key Events This Week")
    st.caption("It's Monday — here's what to watch across the trading week.")
    if week_ahead:
        st.dataframe(pd.DataFrame(week_ahead), hide_index=True)
    if earnings_this_week:
        st.markdown("**Priority earnings reporters this week:**")
        st.dataframe(pd.DataFrame(earnings_this_week), hide_index=True)
>>>>>>> 81638a08212eb30308f3bcd357044f7983b43bc2

st.divider()

# ── Top 5 ─────────────────────────────────────────────────────────────────────

top5_label = "5 Key Things That Happened This Weekend" if is_monday else "5 Biggest Market-Moving Events Yesterday"
section_label(top5_label)
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

st.divider()

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

day_hash = int(hashlib.md5(str(report["report_date"]).encode()).hexdigest(), 16)
quote_text, quote_author = QUOTES[day_hash % len(QUOTES)]

section_label("Quote of the Day")
st.markdown(
    f"<div style='border-left: 3px solid #102a73; padding: 12px 20px; margin: 8px 0;'>"
    f"<span style='font-style:italic; font-size:1.05rem; color:#1f2937;'>\"{quote_text}\"</span>"
    f"<br><br>"
    f"<span style='font-style:normal; font-weight:600; font-size:0.9rem; color:#1f2937;'>"
    f"— {quote_author}</span></div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Daily Pitch ───────────────────────────────────────────────────────────────

section_label("Daily Pitch")
pitch = summary.get("daily_pitch", "")
if pitch:
    fields = {"TRADE": "", "DIRECTION": "", "RATIONALE": "", "RISK": ""}
    for key in fields:
        m = _re.search(rf'{key}:\s*(.+?)(?=\n[A-Z]+:|\Z)', pitch, _re.DOTALL)
        if m:
            fields[key] = m.group(1).strip()

    direction = fields["DIRECTION"].upper()
    if direction == "LONG":
        border_color = "#059669"
        bg_color     = "#f0fdf4"
        chip_class   = "chip chip-green"
    elif direction == "SHORT":
        border_color = "#e11d48"
        bg_color     = "#fff7f9"
        chip_class   = "chip chip-red"
    else:
        border_color = "#102a73"
        bg_color     = "#f0f4ff"
        chip_class   = "chip"

    st.markdown(
        f"<div style='"
        f"background:{bg_color}; "
        f"border: 1px solid {border_color}33; "
        f"border-left: 5px solid {border_color}; "
        f"border-radius: 10px; "
        f"padding: 20px 24px; "
        f"margin-bottom: 12px;'>"
        f"<div style='font-size:1.25rem; font-weight:700; color:{border_color}; margin-bottom:8px;'>"
        f"{safe_md(fields['TRADE'])} "
        f"<span class='{chip_class}' style='font-size:0.78rem; vertical-align:middle;'>"
        f"{fields['DIRECTION']}</span>"
        f"</div>"
        f"<p style='margin:10px 0 4px 0; font-weight:600; color:#1f2937;'>Why:</p>"
        f"<p style='margin:0 0 12px 0; color:#1f2937; line-height:1.6;'>{safe_md(fields['RATIONALE'])}</p>"
        f"<p style='margin:0; font-size:0.85rem; color:#6b7280;'>"
        f"<strong style='color:#1f2937;'>Risk:</strong> {safe_md(fields['RISK'])}"
        f"</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.caption("Daily pitch unavailable — set ANTHROPIC_API_KEY in .env")

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    "<div style='text-align:center; color:#9ca3af; font-size:0.75rem; padding: 8px 0 24px;'>"
    "Market News Dashboard &nbsp;·&nbsp; Data: Yahoo Finance &nbsp;·&nbsp; AI: Claude (Anthropic)"
    "</div>",
    unsafe_allow_html=True,
)
