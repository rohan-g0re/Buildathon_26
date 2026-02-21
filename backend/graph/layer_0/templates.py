"""
Few-shot example templates for the Layer 0 data synthesizer agent.

These are extracted from EXAMPLE_DATA_FORMAT.md and injected into LLM
prompts so the synthesizer replicates the exact structure for any ticker.

See: docs/architecture/LLD_layer_0.md § 4
"""

# ─────────────────────────────────────────────────────────────────────
# Financial Data Template (extracted from EXAMPLE_DATA_FORMAT.md)
# ─────────────────────────────────────────────────────────────────────

FINANCIAL_DATA_TEMPLATE = """
# NovaTech Inc. (NVTK) — Financial Data Package

**Sector:** Technology | **Industry:** Enterprise SaaS
**Market Cap:** $4.2B | **Report Date:** January 31, 2026

---

## Quarterly Revenue

| Quarter | Revenue ($M) | YoY Change | QoQ Change |
|---------|-------------|------------|------------|
| Q1 2025 | 312 | +18.2% | +3.1% |
| Q2 2025 | 298 | +12.4% | -4.5% |
| Q3 2025 | 285 | +8.1% | -4.4% |
| Q4 2025 | 310 | +6.3% | +8.8% |

**Full Year 2025 Revenue:** $1,205M (+10.8% YoY)
**Full Year 2024 Revenue:** $1,088M (+24.0% YoY)

---

## Revenue by Segment

| Segment | Q1 2025 | Q2 2025 | Q3 2025 | Q4 2025 | FY 2025 | YoY Trend |
|---------|---------|---------|---------|---------|---------|-----------|
| Cloud Platform | $198M | $201M | $195M | $218M | $812M | Growing steadily |
| Professional Services | $78M | $65M | $58M | $55M | $256M | Declining fast (-30% Q1→Q4) |
| Legacy On-Premise Licenses | $36M | $32M | $32M | $37M | $137M | Flat / dying |

Cloud Platform now accounts for **67% of total revenue**, up from 58% in FY 2024.

---

## Revenue by Geography

| Region | Annual Revenue ($M) | % of Total |
|--------|-------------------|------------|
| North America | 782 | 64.8% |
| Europe | 265 | 22.0% |
| Asia-Pacific | 120 | 9.9% |
| Rest of World | 38 | 3.2% |

Asia-Pacific grew 22% YoY. North America grew only 7%.

---

## Income Statement (Quarterly)

| Metric | Q1 2025 | Q2 2025 | Q3 2025 | Q4 2025 |
|--------|---------|---------|---------|---------|
| Revenue | $312M | $298M | $285M | $310M |
| Cost of Revenue | $118M | $116M | $112M | $115M |
| **Gross Profit** | **$194M** | **$182M** | **$173M** | **$195M** |
| Gross Margin | 62.2% | 61.1% | 60.7% | 62.9% |
| R&D Expense | $72M | $74M | $76M | $78M |
| SG&A Expense | $93M | $97M | $92M | $82M |
| **Operating Income** | **$29M** | **$11M** | **$5M** | **$35M** |
| Operating Margin | 9.3% | 3.7% | 1.8% | 11.3% |
| **Net Income** | **$21M** | **$5M** | **-$2M** | **$26M** |
| EPS (diluted) | $0.42 | $0.10 | -$0.04 | $0.51 |

Note: SG&A dropped sharply in Q4 ($92M → $82M) due to a hiring freeze and headcount reduction in the sales org. R&D spending has been increasing every quarter as the company invests in AI features.

---

## Balance Sheet (as of December 31, 2025)

| Assets | Amount |
|--------|--------|
| Cash & Equivalents | $620M |
| Short-Term Investments | $340M |
| Accounts Receivable | $285M |
| Total Current Assets | $1,480M |
| **Total Assets** | **$3,120M** |

| Liabilities & Equity | Amount |
|-----------------------|--------|
| Current Liabilities | $580M |
| Deferred Revenue | $195M |
| Long-Term Debt | $800M |
| Total Liabilities | $1,640M |
| **Total Equity** | **$1,480M** |
| Retained Earnings | $410M |

Net debt position: $800M debt - $620M cash = **$180M net debt**

---

## Cash Flow (FY 2025)

| Metric | FY 2025 |
|--------|---------|
| Operating Cash Flow | $185M |
| Capital Expenditure | -$78M |
| **Free Cash Flow** | **$107M** |
| Stock Buyback | -$90M |
| Debt Repayment | -$60M |
| Acquisitions | -$45M |

Free cash flow margin: 8.9%. The company is spending almost all its FCF on buybacks, debt, and acquisitions.

---

## Stock Price (Last 8 Months)

| Date | Close Price | Volume (M shares) |
|------|------------|-------------------|
| Jul 1, 2025 | $84.20 | 2.1 |
| Aug 1, 2025 | $78.50 | 3.4 |
| Sep 1, 2025 | $71.30 | 4.2 |
| Oct 1, 2025 | $68.10 | 2.8 |
| Nov 1, 2025 | $72.80 | 2.3 |
| Dec 1, 2025 | $79.60 | 2.0 |
| Jan 1, 2026 | $82.40 | 1.9 |
| Jan 31, 2026 | $85.10 | 2.5 |

52-week high: $92.40 (Mar 2025). 52-week low: $66.80 (Sep 2025). Current price is 8% below ATH.

---

## Key Ratios

| Ratio | Value | Sector Avg |
|-------|-------|------------|
| P/E Ratio | 34.2x | 38.5x |
| Forward P/E | 28.1x | 32.0x |
| P/B Ratio | 2.84x | 4.1x |
| P/S Ratio | 3.48x | 7.2x |
| EV/EBITDA | 22.6x | 28.0x |
| Debt-to-Equity | 0.54 | 0.45 |
| Current Ratio | 2.55 | 2.1 |
| ROE | 3.4% | 12.5% |
| Net Dollar Retention | 108% | 115% |
| Rule of 40 | 22.8 | 35+ |

NovaTech trades at a significant discount to SaaS peers on most valuation multiples. ROE and Rule of 40 are well below sector benchmarks.

---

## Key Business Metrics

| Metric | Value |
|--------|-------|
| Total Customers | 4,200 |
| Enterprise Customers (>$100K ARR) | 380 |
| Annual Recurring Revenue (ARR) | $812M |
| Net Dollar Retention | 108% |
| Customer Acquisition Cost | $45K |
| LTV/CAC Ratio | 4.2x |
| Employees | 3,100 |
| Revenue per Employee | $389K |

---

## Management Guidance (FY 2026)

- **Revenue:** $1,260M – $1,300M (4.6% – 7.9% growth)
- **Operating Margin:** 8% – 11%
- **Commentary:** Management expects continued cloud platform growth offset by legacy license decline. The company is investing heavily in AI-powered features and expects these to drive expansion in H2 2026. A restructuring charge of $15-20M is expected in Q1 2026 related to headcount reduction in Professional Services.

---

## Recent Corporate Events

- **Dec 15, 2025** — Announced acquisition of DataMesh AI for $45M in cash, adding AI/ML data pipeline capabilities to the cloud platform.
- **Nov 2, 2025** — CFO Sarah Chen resigned. Interim CFO appointed (Mark Torres, VP of Finance).
- **Oct 18, 2025** — Launched NovaTech AI Assistant, an AI copilot embedded in the cloud platform. 15% of enterprise customers activated within 3 months.
- **Sep 5, 2025** — Lost a $12M annual contract with FinServ Corp to competitor CloudScale Systems.
- **Aug 20, 2025** — Announced $90M stock buyback program over 12 months.
""".strip()


# ─────────────────────────────────────────────────────────────────────
# News & Sentiment Data Template (extracted from EXAMPLE_DATA_FORMAT.md)
# ─────────────────────────────────────────────────────────────────────

NEWS_DATA_TEMPLATE = """
# NovaTech Inc. (NVTK) — Market & Sentiment Brief

**Data as of:** January 31, 2026

---

## Recent News Coverage

### 1. NovaTech Q4 Earnings Beat Estimates, But Full-Year Growth Slows to Single Digits
**Source:** TechCrunch | **Date:** Jan 28, 2026 | **Sentiment:** Mixed

NovaTech reported Q4 revenue of $310M, beating analyst consensus of $302M. However, full-year revenue growth of 10.8% marks a significant deceleration from 24% in FY2024. The company's AI Assistant product showed promising early adoption with 15% of enterprise customers activating it within three months of launch.

### 2. CloudScale Systems Raises $200M Series D, Eyes NovaTech's Enterprise Customers
**Source:** Bloomberg | **Date:** Jan 15, 2026 | **Sentiment:** Negative for NVTK

CloudScale Systems, NovaTech's primary competitor in enterprise cloud platforms, raised $200M at a $3.8B valuation. The company has won several NovaTech customers in the past year, including the high-profile FinServ Corp deal. CEO claims they're "on track to reach $500M ARR by end of 2026."

### 3. Enterprise SaaS Spending Expected to Rebound in H2 2026, Gartner Says
**Source:** Reuters | **Date:** Jan 10, 2026 | **Sentiment:** Positive for sector

Gartner's latest forecast projects enterprise SaaS spending to grow 14% in 2026, up from 9% in 2025, driven by AI integration. Companies with embedded AI features are expected to see disproportionate budget allocation. "The AI premium is real — buyers are willing to pay 20-30% more for AI-native platforms," said VP analyst Mark Smith.

### 4. NovaTech CFO Departure Raises Governance Questions
**Source:** Wall Street Journal | **Date:** Nov 5, 2025 | **Sentiment:** Negative

The sudden resignation of NovaTech CFO Sarah Chen has raised questions among investors about the company's financial controls and strategic direction. Chen had been instrumental in the company's transition to a subscription model. Two board members have also quietly stepped down in the past six months.

### 5. NovaTech's DataMesh Acquisition Could Be a Sleeper Hit, Analysts Say
**Source:** Barron's | **Date:** Dec 20, 2025 | **Sentiment:** Positive

Several analysts have upgraded their outlook following the DataMesh AI acquisition. DataMesh's real-time data pipeline technology could accelerate NovaTech's AI roadmap by 12-18 months. "At $45M, this looks like a steal," wrote Morgan Stanley analyst Lisa Park.

### 6. Enterprise Software M&A Heats Up as Big Tech Eyes Mid-Cap SaaS
**Source:** Financial Times | **Date:** Jan 22, 2026 | **Sentiment:** Positive for NVTK

Multiple sources indicate that large technology companies are actively evaluating acquisition targets in the mid-cap enterprise SaaS space, with companies valued between $3-8B being particularly attractive. NovaTech, Zenith Cloud, and PlatformIQ have all been mentioned in banker conversations.

---

## Reddit / Social Sentiment

### r/stocks — "NVTK - Is the turnaround real or a dead cat bounce?"
**Date:** Jan 29, 2026 | **Score:** 342 upvotes

Top comments:
> "Q4 was solid but the growth deceleration is concerning. They went from 24% to 10% in one year. Cloud segment is carrying the whole company."

> "The AI Assistant adoption at 15% of enterprise customers in just 3 months is actually impressive. If that hits 50% by mid-2026, this stock re-rates hard."

> "I'm worried about CloudScale eating their lunch. Lost FinServ and probably others we don't know about."

> "Insider buying from the CEO in December. He bought $2M worth at $74. That's usually a good signal."

> "The CFO departure is the real red flag nobody is talking about. Two board members also left."

### r/wallstreetbets — "NVTK calls printing after earnings beat"
**Date:** Jan 29, 2026 | **Score:** 890 upvotes

Top comments:
> "AI + SaaS + potential acquisition target = moon. Loading up on March calls."

> "This company has been a value trap for 6 months, one good quarter doesn't change that."

> "Somebody bought 10,000 March $90 calls last week. Smart money knows something."

### r/investing — "Deep dive: NovaTech — undervalued or growth story over?"
**Date:** Jan 20, 2026 | **Score:** 215 upvotes

Top comments:
> "Professional Services revenue is in freefall. -30% from Q1 to Q4. They're basically becoming a pure cloud company whether they want to or not."

> "Net dollar retention at 108% is below the SaaS benchmark of 115-120%. Existing customers aren't expanding fast enough."

> "At 3.5x P/S with improving margins and AI optionality, I think this is undervalued relative to peers trading at 8-12x."

---

## Prediction Market Signals (Polymarket)

| Event | Probability | Volume |
|-------|------------|--------|
| NovaTech acquired by Big Tech before Jan 2027? | **22%** | $450K |
| NovaTech ARR exceeds $1B by end of 2026? | **35%** | $120K |
| CloudScale Systems IPOs in 2026? | **58%** | $890K |

---

## Competitor Activity

### CloudScale Systems (Private)
- Raised **$200M Series D** at $3.8B valuation (Jan 2026)
- Claims **180% net dollar retention** (vs NovaTech's 108%)
- Won 40+ enterprise accounts from legacy vendors in 2025, including NovaTech's FinServ Corp
- AI-first architecture perceived as "a generation ahead"
- 58% odds of IPO in 2026 on Polymarket

### Zenith Cloud (ZNTH)
- Announced **strategic partnership with Microsoft** for Azure-native integration (Jan 2026)
- Now a preferred platform on Azure Marketplace
- Could pressure NovaTech's multi-cloud positioning

---

## Analyst Ratings

| Firm | Rating | Target Price | Date |
|------|--------|-------------|------|
| Morgan Stanley | Overweight | $98 | Jan 29, 2026 |
| Goldman Sachs | Neutral | $85 | Jan 29, 2026 |
| JP Morgan | Overweight | $95 | Jan 20, 2026 |
| Barclays | Equal Weight | $80 | Dec 15, 2025 |

**Average target:** $89.50 (5.2% upside from current $85.10)
""".strip()
