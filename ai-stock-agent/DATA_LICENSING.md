# Data licensing: what must change before this becomes a commercial product

Status as of 2026-09-25. **Not legal advice.** Terms change; read each provider's current terms and have a
securities/IP lawyer review the launch plan. "Confirmed" means read on the provider's own page or a
current source this session; "not confirmed" means I could not verify it and it must be checked.

## What the system uses today

| Data | Source | Where | Terms position |
|---|---|---|---|
| Prices: daily and 60-minute bars for ~470 stocks | Yahoo Finance via `yfinance` | `ultimate_market_scanner.py` (21 call sites), `agents/data_agent.py`, `swing_trader.py`, `enhancements/multi_timeframe.py`, `paper_analysis.py` | **Confirmed personal/non-commercial.** yfinance itself says it is for research and educational use and is not affiliated with Yahoo; it reads unofficial endpoints. |
| Live quotes on the dashboard | Yahoo chart endpoint (unofficial) | `dashboard/server.py` `_meta()` | Same as above. Only shown to invited, signed-in testers today. |
| Fundamentals, market context, institutional holders | Yahoo via `yfinance` | `agents/fundamental_agent.py`, `agents/market_context_agent.py`, `tools/institutional_tool.py` | Same as above. |
| News | NewsAPI, Finnhub, Alpha Vantage free tiers | `agents/enhanced_news_agent.py` | Finnhub free: **confirmed non-commercial** (monetised or redistributing apps need a paid plan). NewsAPI free developer tier and Alpha Vantage free tier: not confirmed this session, and NewsAPI's free tier is commonly development-only. Check. |
| Language model | OpenAI API | `agents/autonomous_reasoning_agent.py`, `shadow.py` | Commercial use is allowed under OpenAI's API terms; check output-use and disclosure rules for your use case. |

## What the public page already avoids

`/public` shows only audited aggregates and the hash chain; raw decisions are released 45 days late. It shows no live
prices, no current signals and no vendor data. That reduces redistribution exposure but does not remove the question of
whether *running the pipeline* on Yahoo data for a commercial venture is permitted. Treat it as an open risk, not solved.

## Options for licensed data (costs as found, verify before relying on them)

| Provider | What was found | Fit |
|---|---|---|
| Massive (formerly Polygon.io, rebranded 2025-10-30) | Individual plans (free, ~$29, ~$79, ~$199 for real-time) are for personal use. The **Stocks Business plan is $2,499/month**; add-ons run $499-$1,999/month. Its page does not say whether the licence covers displaying data to end users or redistribution: **must ask sales.** An unrelated review site quoted "$50/month for business"; it did not match the provider's own page, so do not use that figure. | Full coverage, expensive. |
| Alpaca market data | Free plan is IEX-exchange data, 15-minute delayed over REST, 200 requests/minute (from Alpaca's docs). Commercial and display terms: **not confirmed**, read Alpaca's data terms. | Cheapest to try; IEX-only volume is not full-market. |
| Finnhub paid | Free tier is non-commercial; commercial licences by contacting sales. Price not confirmed. | Also covers news and fundamentals. |
| Others not checked | Twelve Data, Tiingo, Databento, Financial Modeling Prep, EOD Historical Data. | Compare on: commercial-use clause, display rights, intraday 60m bars, 470-ticker throughput. |

## The decision that drives everything (yours)

"Free to use commercially" can mean very different things, and the cost range is roughly $0 to $2,500+/month:

1. **Free, non-monetised research and education site** (no ads, no paid tier, no signals): lowest data risk and cost, but Yahoo's
   personal-use position still applies to a running public service, so get a lawyer's view on whether it is acceptable.
2. **Product that ends up with revenue** (ads, subscriptions, sponsorship, a company behind it): assume you need a licensed
   feed. Ask each vendor in writing: is commercial display to end users permitted, is redistribution of derived signals permitted, per-user fees?
3. **End-of-day-only product**: the scanner currently uses 60-minute bars. Moving to daily bars would allow far cheaper data,
   but changes the product and needs its own re-validation, since every result so far is for the hourly design.

## Engineering work for the swap (not started, on purpose)

The Yahoo calls are spread across about 40 sites in 7 files. A safe swap needs: (1) a provider chosen and a key to test against,
(2) one `market_data` interface (`history`, `quote`, `fundamentals`) with Yahoo as the default, (3) each call site moved behind
it and verified against Yahoo output on the same tickers, (4) a shadow run comparing the two providers' bars before cutover.
Doing this without a chosen provider would risk breaking a working production scanner for no verified gain.

## Regulatory reminder

Showing named stocks with BUY labels to the public can be treated as investment advice in some jurisdictions. Keep the public
product general and educational, publish delayed data only, avoid personalised recommendations and brokerage links, and add
prominent disclaimers (already on `/public`). Confirm with a securities lawyer before launch.
