# dex/dex_analysis.py

import requests
from collections import Counter
import logging
from config.config import DEXSCREENER_SEARCH_URL

def analyze_tickers_with_market_data(tickers):
    ticker_counts = Counter(tickers)
    ticker_analysis = {}

    for ticker, mentions in ticker_counts.items():
        response = requests.get(f"{DEXSCREENER_SEARCH_URL}?q={ticker}")
        if response.status_code == 200:
            data = response.json()
            entries = []
            for pair in data.get("pairs", [])[:3]:
                entry = {
                    "price_usd": pair.get("priceUsd"),
                    "liquidity_usd": pair["liquidity"].get("usd", 0),
                    "market_cap": pair.get("marketCap", 0),
                    "fdv": pair.get("fdv", 0)
                }
                entries.append(entry)
            ticker_analysis[ticker] = {
                "mentions": mentions,
                "entries": entries
            }
        else:
            logging.error(f"Failed to fetch data for ticker {ticker} from Dexscreener")

    if ticker_counts:
        most_mentioned_ticker = max(ticker_counts, key=ticker_counts.get)
        total_mentions = sum(ticker_counts.values())
        consistency_score = ticker_counts[most_mentioned_ticker] / total_mentions
    else:
        consistency_score = 0

    return consistency_score, ticker_analysis
