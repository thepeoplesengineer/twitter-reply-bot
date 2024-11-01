# dex/dex_analysis.py

import requests
from collections import Counter
import logging
from config.config import DEXSCREENER_SEARCH_URL
from utils.twitter_utils import fetch_user_tweets

def fetch_ticker_data(ticker):
    """
    Fetches data from the Dexscreener API for a specific ticker.
    """
    try:
        response = requests.get(f"{DEXSCREENER_SEARCH_URL}?q={ticker}")
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch data for ticker {ticker} from Dexscreener: Status {response.status_code}")
            return None
    except requests.RequestException as e:
        logging.error(f"Exception occurred while fetching data for ticker {ticker}: {e}")
        return None

def analyze_ticker_mentions(tickers):
    """
    Counts ticker mentions in the provided list of tickers.
    """
    return Counter(tickers)

def analyze_tickers_with_market_data(tickers):
    """
    Analyzes the consistency of ticker mentions, fetching market data
    and computing a consistency score.
    """
    ticker_counts = analyze_ticker_mentions(tickers)
    ticker_analysis = {}

    for ticker, mentions in ticker_counts.items():
        data = fetch_ticker_data(ticker)
        if data and "pairs" in data:
            entries = []
            for pair in data["pairs"][:3]:  # Limit to the top 3 entries for brevity
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
            logging.error(f"Failed to fetch or parse data for ticker {ticker}")

    # Calculate the consistency score
    if ticker_counts:
        most_mentioned_ticker = max(ticker_counts, key=ticker_counts.get)
        total_mentions = sum(ticker_counts.values())
        consistency_score = ticker_counts[most_mentioned_ticker] / total_mentions
    else:
        consistency_score = 0

    return consistency_score, ticker_analysis

def run_consistency_analysis(twitter_api, user_id):
    # Step 1: Fetch user tweets
    tweets = fetch_user_tweets(twitter_api, user_id)

    # Step 2: Extract tickers from tweets
    ticker_pattern = r'\$[A-Za-z0-9]+'  # Regex for finding tickers
    tickers = [ticker for tweet in tweets for ticker in re.findall(ticker_pattern, tweet)]

    # Step 3: Analyze ticker mentions and get market data
    consistency_score, ticker_analysis = analyze_tickers_with_market_data(tickers)

    # Step 4: Construct the response with analysis results
    reply_text = f"Consistency Score: {consistency_score:.2f}\nTop Tickers:\n"
    for ticker, details in ticker_analysis.items():
        reply_text += f"{ticker}: {details['mentions']} mentions\n"
        for idx, entry in enumerate(details["entries"][:3], start=1):
            reply_text += (
                f"  Entry {idx}: Price: ${entry['price_usd']}, "
                f"Liquidity: ${entry['liquidity_usd']}, Market Cap: ${entry['market_cap']}, "
                f"FDV: ${entry['fdv']}\n"
            )

    return reply_text[:280]  # Truncate to 280 characters for Twitter

def extract_tickers(tweets):
    """
    Extracts ticker symbols from a list of tweet texts using regex.
    """
    import re
    ticker_pattern = re.compile(r'\$[A-Za-z0-9]+')
    tickers = []
    for tweet in tweets:
        found_tickers = ticker_pattern.findall(tweet)
        tickers.extend(found_tickers)
    return tickers

