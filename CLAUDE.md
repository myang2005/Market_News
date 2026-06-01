# Market News Dashboard

## Project Overview

The **Market News Dashboard** is a daily automated markets briefing system that delivers a concise, high-signal market update every morning at **7:00 AM Eastern Time**.

The dashboard should only generate and deliver the daily update if the **U.S. stock market was open on the prior business day**. When triggered, it will summarize the previous day’s market closing levels, overnight market moves, key macroeconomic developments, and important news across equities, rates, FX, commodities, credit, and global markets.

The goal is to replace the current manual process of checking individual index prices, treasury yields, futures, commodities, currencies, and market newsletters with a single centralized dashboard that provides the most relevant information before the market opens.

---

## Problem Statement

Currently, getting a useful morning markets update requires manually collecting information from multiple sources:

- Checking closing prices for major indexes and asset classes individually
- Looking up treasury yields and yield-curve spreads
- Reading several market newsletters and news sources
- Tracking overnight developments across global markets
- Monitoring macroeconomic releases, Fed commentary, earnings, and geopolitical events

This process is time-consuming and fragmented. The dashboard should automate the data collection and summarization process so that the user can quickly understand what happened yesterday, what changed overnight, and what matters for the trading day ahead.

---

## Project Goal

Build a dashboard that provides a **daily markets update at 7:00 AM EST**, conditioned on whether the stock market was open the previous day.

The dashboard should include:

1. Prior-day closing prices for key indexes and market indicators
2. Daily percentage changes and notable moves
3. Overnight global market developments
4. Key macro, central bank, geopolitical, corporate, rates, credit, FX, and commodity news
5. A concise summary of the most important market takeaways
6. A forward-looking section covering the day’s major scheduled events

---

## Core User Story

As a user preparing for the market day, I want to receive a dashboard every morning at 7:00 AM EST with the previous trading day’s market closes and the most important overnight news, so that I can quickly understand the market backdrop without manually checking multiple sources.

### Logic Requirements

- Check whether the prior day was a valid U.S. equity market trading day.
- Exclude weekends.
- Exclude U.S. market holidays.
- Account for early closes where applicable.
- If the prior day was not a trading day, the system should:
  - Send a short message saying no full update is available because the market was closed.

### Example Behavior

- Tuesday at 7:00 AM: report Monday’s market close.
- Saturday at 7:00 AM: report Friday’s market close, if Friday was open.
- Day after a market holiday: note that no prior trading day update is available.

---

## Dashboard Sections

## 1. Executive Market Summary

A short top-level summary of the market environment.

This section should answer:

- Was risk sentiment positive or negative?
- What were the biggest asset-class moves?
- What drove markets yesterday?
- What changed overnight?
- What should the user pay attention to today?

### Example Format

```text
Markets finished mixed yesterday as large-cap tech outperformed while small caps lagged. Treasury yields moved higher after stronger-than-expected economic data, pushing the 2s10s curve slightly flatter. Overnight, Asian equities were mostly higher, oil traded lower, and the dollar was little changed. Today, focus is on jobless claims, Fed speakers, and major tech earnings after the close.
```

---

## 2. Major Indexes to Track Daily

### Equities

| Asset | Ticker / Symbol | Purpose |
|---|---:|---|
| S&P 500 | SPX | Broad U.S. market benchmark |
| Nasdaq 100 | NDX | Tech-heavy index and growth sentiment indicator |
| Dow Jones Industrial Average | DJIA | Blue-chip industrial gauge |
| Russell 2000 | RUT | Small-cap performance and risk appetite |
| VIX | VIX | Implied volatility / fear index; critical for sales & trading context |

### International Equity Indexes

| Asset | Region | Purpose |
|---|---|---|
| FTSE 100 | United Kingdom | European and global macro context |
| DAX | Germany | Eurozone industrial and risk sentiment indicator |
| Nikkei 225 | Japan | Asian market and Japan macro context |

### Fixed Income

| Asset | Purpose |
|---|---|
| 2-Year U.S. Treasury Yield | Fed policy expectations and front-end rates |
| 10-Year U.S. Treasury Yield | Benchmark long-term rate and macro risk gauge |
| 30-Year U.S. Treasury Yield | Long-end duration and fiscal/rates sentiment |
| 2s10s Spread | Yield curve / recession indicator |
| Investment Grade Credit Spreads | Corporate credit risk conditions |
| High Yield Credit Spreads | Risk appetite and credit stress indicator |

### Currencies / FX

| Asset | Purpose |
|---|---|
| DXY U.S. Dollar Index | Broad dollar strength |
| EUR/USD | Major developed market FX pair |
| USD/JPY | Rates differential and Japan macro sensitivity |
| GBP/USD | U.K. macro and dollar sentiment |

### Commodities

| Asset | Purpose |
|---|---|
| WTI Crude Oil | U.S. oil benchmark and inflation input |
| Brent Crude Oil | Global oil benchmark |
| Gold | Safe-haven and real-rate sensitivity |
| Natural Gas | Energy market and seasonal relevance |

### Other Markets

| Asset | Purpose |
|---|---|
| Fed Funds Futures | Implied Fed rate expectations |
| Bitcoin | Crypto and broader macro risk sentiment |

---

## 3. Market Data Requirements

For each tracked market/index/security, the dashboard should capture:

- Prior close
- Daily percentage change
- Overnight / futures move only if significant

### Suggested Display Format

| Market | Last / Close | Daily Change | Daily % Change | Notes |
|---|---:|---:|---:|---|
| S&P 500 | TBD | TBD | TBD | Broad market benchmark |
| Nasdaq 100 | TBD | TBD | TBD | Growth / tech sentiment |
| 10Y Treasury Yield | TBD | TBD | TBD | Benchmark rate |
| DXY | TBD | TBD | TBD | Dollar strength |
| WTI Crude | TBD | TBD | TBD | Energy / inflation input |

---

## 4. News & Events to Track

## Macro / Economic Data

The dashboard should track the economic release calendar and flag major upcoming or recently released data. 

### Key Events

- FOMC meetings
- Fed minutes
- CPI inflation report
- PPI inflation report
- Nonfarm Payrolls / Jobs Report
- GDP prints
- PCE inflation
- ISM PMI
- Retail sales
- Initial and continuing jobless claims

### Importance Ranking

| Event | Importance | Notes |
|---|---:|---|
| FOMC meetings / Fed decision | Very High | Most market-moving scheduled macro event |
| CPI | Very High | Major inflation and Fed expectations driver |
| Jobs Report / NFP | Very High | Usually first Friday of the month; major volatility event |
| PPI | High | Inflation pipeline signal |
| PCE | High | Fed-preferred inflation measure |
| ISM PMI | Medium / High | Growth and business cycle indicator |
| Retail Sales | Medium / High | Consumer demand signal |
| Jobless Claims | Medium | Labor market trend indicator |

---

## 5. Central Bank Monitoring 

The dashboard should monitor major central bank decisions, speakers, minutes, and policy shifts. 

### Central Banks to Track

- Federal Reserve
- European Central Bank
- Bank of Japan
- Bank of England

### Fed Speaker Tracking

The system should flag:

- Fed speakers scheduled for the day
- Notable comments from the prior day
- Whether comments were interpreted as hawkish, dovish, or neutral
- Any change in implied rate expectations after the comments

### Central Bank Output Format

```text
Central Banks: Fed Governor comments leaned hawkish yesterday, emphasizing that inflation progress remains incomplete. Fed funds futures now imply slightly lower odds of a near-term cut. ECB officials continued to signal data dependence, while BOJ commentary focused on wage growth and inflation persistence.
```

---

## 6. Geopolitics & Macro Themes

The dashboard should identify market-relevant geopolitical developments and major macro themes.

### Themes to Track

- Trade policy and tariffs
- Sanctions
- Energy supply disruptions
- Elections in major economies
- Military conflict or escalation risk
- Major fiscal policy announcements
- Sovereign debt concerns
- China growth or policy developments

### Output Goal

This section should only include developments that are likely to affect markets, such as:

- Oil supply shocks
- Trade restrictions
- Currency interventions
- Election surprises
- Fiscal stress
- Sanctions affecting commodities or financial flows

---

## 7. Corporate / Equities Monitoring

The dashboard should track major equity-market events and company-specific catalysts.

### Items to Track

- Earnings season
- Major reporters for the week
- Magnificent 7 earnings
- Large financial institutions
- Semiconductors and major tech names
- Analyst upgrades and downgrades on major names
- Major M&A activity
- Large guidance revisions
- Significant pre-market and after-hours movers

### Earnings Watchlist

Priority companies should include:

- Apple
- Microsoft
- Nvidia
- Amazon
- Alphabet
- Meta
- Tesla
- JPMorgan Chase
- Goldman Sachs
- Morgan Stanley
- Bank of America
- Reddit
- Major semiconductor names
- Major energy companies
- Large retailers during retail earnings season

---

## 8. Credit & Rates Monitoring

The dashboard should include a focused section on rates and credit because these are central to market direction and desk commentary.

### Items to Track

- 2Y, 10Y, and 30Y Treasury yields
- 2s10s spread
- Treasury auction schedule
- 3Y, 10Y, and 30Y auctions
- Auction tails or stops-through
- Bid-to-cover ratios
- Dealer takedown
- Investment grade corporate bond issuance
- High yield issuance
- IG and HY credit spreads
- Sovereign debt news, especially EU periphery

### Output Goal

The dashboard should explain whether rates moved because of:

- Economic data
- Fed commentary
- Inflation expectations
- Treasury supply / auctions
- Risk sentiment
- Global rates moves

---

## 9. Overnight Market Update

Because the dashboard is delivered before the U.S. market opens, it should include an overnight section.

### Overnight Items

- Asian equity market performance
- European equity market performance
- U.S. equity futures
- Treasury futures or overnight yield moves
- Dollar moves
- Oil and gold moves
- Major overnight news headlines
- Pre-market earnings or guidance
- Major geopolitical developments

### Example Format

```text
Overnight: Asian equities were mostly higher, led by Japan, while Hong Kong lagged on renewed China growth concerns. European futures point to a modestly positive open. U.S. equity futures are slightly higher, Treasury yields are little changed, and oil is lower after reports of higher expected supply.
```

---

## 10. Daily Report Structure

The final daily dashboard should be organized in a repeatable format:

1. Executive Market Summary
2. Prior-Day Market Snapshot
3. Overnight Market Moves
4. Rates & Credit
5. FX & Commodities
6. Macro Calendar
7. Central Banks
8. Corporate / Earnings Watch
9. Geopolitics & Macro Themes
10. Top 5 Things to Watch Today

---

## Suggested Dashboard Output Template

```markdown
# Daily Markets Update — YYYY-MM-DD

## Executive Summary
- [Three to five bullets summarizing the market backdrop]

## Prior-Day Market Snapshot
| Market | Close | Change | % Change | Comment |
|---|---:|---:|---:|---|
| S&P 500 | | | | |
| Nasdaq 100 | | | | |
| Dow Jones | | | | |
| Russell 2000 | | | | |
| VIX | | | | |

## Global Markets
| Market | Level | Change | % Change | Comment |
|---|---:|---:|---:|---|
| FTSE 100 | | | | |
| DAX | | | | |
| Nikkei 225 | | | | |
| Hang Seng | | | | |

## Rates & Credit
| Indicator | Level | Change | Comment |
|---|---:|---:|---|
| 2Y Treasury | | | |
| 10Y Treasury | | | |
| 30Y Treasury | | | |
| 2s10s Spread | | | |
| IG Spreads | | | |
| HY Spreads | | | |

## FX & Commodities
| Asset | Level | Change | % Change | Comment |
|---|---:|---:|---:|---|
| DXY | | | | |
| EUR/USD | | | | |
| USD/JPY | | | | |
| GBP/USD | | | | |
| WTI Crude | | | | |
| Brent Crude | | | | |
| Gold | | | | |
| Natural Gas | | | | |
| Bitcoin | | | | |

## Overnight News
- [Most important overnight development]
- [Global markets update]
- [Central bank or macro update]

## Macro Calendar
| Time | Event | Consensus | Prior | Importance |
|---|---|---:|---:|---|
| | | | | |

## Central Banks (Only include this section or one of the banks if something of significance came up, or else omit this section)
- Fed:
- ECB:
- BOJ:
- BOE:

## Corporate / Earnings Watch
- Major reporters:
- Notable upgrades/downgrades:
- M&A activity:
- Pre-market movers:

## Credit & Rates Watch
- Treasury auctions:
- Corporate issuance:
- Credit spread moves:
- Sovereign debt headlines:

## Top 5 Things to Watch Today
1. 
2. 
3. 
4. 
5. 
```

---

## Data Source Requirements

The project will likely need multiple data sources.

### Market Data Sources

Potential sources:

- Yahoo Finance API or unofficial market data library
- Polygon.io
- Alpha Vantage
- IEX Cloud
- Nasdaq Data Link
- Bloomberg, if available
- Refinitiv, if available
- FRED for rates, spreads, and macro series
- Treasury.gov for auction data
- CME FedWatch or futures-derived rate probabilities

### News Sources

Potential sources:

- Financial Times
- Wall Street Journal
- Bloomberg
- Reuters
- CNBC
- MarketWatch
- Morning Brew / market newsletters
- Axios Markets
- The Daily Shot
- Fed official calendar
- Company investor relations calendars
- Earnings calendars

### Economic Calendar Sources

Potential sources:

- Investing.com economic calendar
- Trading Economics
- Econoday
- Bloomberg calendar, if available
- Forex Factory calendar
- Official government release calendars:
  - Bureau of Labor Statistics
  - Bureau of Economic Analysis
  - Census Bureau
  - Federal Reserve

---

## Functional Requirements

### Scheduling

- Run automatically at 7:00 AM EST.
- Check whether the previous day was a U.S. equity trading day.
- Generate report only when appropriate.

### Data Collection

- Pull prior-day close data for all tracked markets.
- Pull overnight futures and global market moves where available.
- Pull rates, credit, FX, commodities, and crypto data.
- Pull scheduled macro events for the current day.
- Pull relevant market news from selected sources.

### Processing

- Calculate daily changes and percentage changes.
- Calculate 2s10s yield spread.
- Identify unusually large moves.
- Rank news by likely market impact.
- Summarize newsletters and news into concise takeaways.

### Dashboard Generation

- Generate a clean Web dashboard.
- Include tables for market data (if possible, on the dashboard label the percent changes >0 in green and <0 in red).
- Include bullet summaries for news.
- Highlight the most important moves and events.

---

## Non-Functional Requirements

- Reliable daily execution
- Clear and readable formatting
- Accurate timestamps
- Source attribution for news summaries
- Graceful handling of missing data
- Avoid excessive noise or irrelevant headlines
- Configurable list of tickers and news sources

---

## Market Impact Ranking Framework

The dashboard should prioritize information based on expected market relevance.

### Highest Priority

- Fed decisions and FOMC communication
- CPI, payrolls, and major inflation/labor data
- Large moves in rates, oil, dollar, or equity futures
- Major geopolitical shocks
- Major earnings from mega-cap companies
- Credit stress signals

### Medium Priority

- Retail sales, ISM, GDP, PCE, jobless claims
- Central bank speakers
- Treasury auctions
- Sector-specific earnings
- Analyst actions on major companies

### Lower Priority

- Minor company news
- Small single-stock moves
- Non-market-moving political headlines
- Regional data releases with limited global impact

---

## MVP Scope

The first version should focus on producing a reliable daily report with core market data and concise news summaries.

### MVP Features

- 7:00 AM EST scheduled run
- Prior trading day check
- U.S. equity indexes:
  - S&P 500
  - Nasdaq 100
  - Dow Jones
  - Russell 2000
  - VIX
- Treasury yields:
  - 2Y
  - 10Y
  - 30Y
  - 2s10s spread
- FX:
  - DXY
  - EUR/USD
  - USD/JPY
  - GBP/USD
- Commodities:
  - WTI
  - Brent
  - Gold
  - Natural Gas
- Bitcoin
- Top overnight news headlines
- Macro calendar for the day
- Top 5 things to watch

---

## Future Enhancements

- Add interactive charts
- Add historical trend sparklines
- Add AI-generated summary of multiple newsletters
- Add sentiment tagging for news
- Add alerting for unusually large market moves
- Add earnings calendar integration
- Add Fed speaker classification as hawkish/dovish/neutral
- Add credit spread charts
- Add rate-cut probability tracker
- Add pre-market movers
- Add sector ETF performance
- Add custom watchlists
- Add mobile-friendly dashboard view

---

## Suggested Technical Architecture

### Data Pipeline

1. Scheduler triggers workflow at 7:00 AM EST.
2. Market calendar check determines whether the prior day was a trading day.
3. Data ingestion pulls market prices, rates, FX, commodities, crypto, and calendar data.
4. News ingestion pulls headlines and newsletters.
5. Processing layer calculates changes, spreads, and ranks important items.
6. Summarization layer produces concise market commentary.
7. Dashboard renderer formats the final report.
8. Delivery layer sends or displays the dashboard.

### Possible Stack

- Python for data collection and processing
- Pandas for market data tables
- APScheduler, cron, GitHub Actions, or cloud scheduler for automation
- yfinance, FRED API, Polygon, Alpha Vantage, or other data providers
- News API or RSS feeds for headlines
- LLM for summarization
- Streamlit, Dash, Next.js, or static HTML for dashboard

---

## Open Questions

- Which data provider will be used for reliable market prices?
- Which newsletters and news sources should be included?
- Should the report include charts or only tables and summaries?
- Should the dashboard include only prior-day closes, or also pre-market futures?
- Should the system save historical daily reports?
- Should the dashboard support alerts for unusually large market moves?

---

## Success Criteria

The project is successful when:

- A dashboard is automatically generated at 7:00 AM EST after valid U.S. market trading days.
- The dashboard includes accurate prior-day closes for all required indexes and asset classes.
- The dashboard summarizes the most important prior-day and overnight market news.
- The report is concise enough to read quickly but detailed enough to support market preparation.
- Manual checking of individual tickers, indexes, newsletters, and calendars is significantly reduced.

---

## Project Name

**Market News Dashboard**
