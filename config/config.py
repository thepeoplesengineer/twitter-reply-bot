

# config/config.py
# centralizes all constants

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twitter API credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Dexscreener API URL
DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"

# Engagement target for rewards
ENGAGEMENT_TOTAL_TARGET = 5

# File paths
REPLIED_MENTIONS_FILE = "replied_mentions.txt"

# Reward item options
ITEM_OPTIONS = ["Wood", "Bacon", "Stone", "Iron", "Water"]
