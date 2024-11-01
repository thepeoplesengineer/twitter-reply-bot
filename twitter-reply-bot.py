import tweepy
import sqlite3
import threading
import schedule
import time
import os
import random
from datetime import datetime, timedelta
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from dotenv import load_dotenv
import logging
import requests
import re
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Dexscreener API URL
DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"

# File to store replied mentions
REPLIED_MENTIONS_FILE = "replied_mentions.txt"

# Initialize SQLite for engagements and inventory
conn = sqlite3.connect("engagements.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS engagements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        engagement_type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        username TEXT NOT NULL,
        item TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        last_checked TIMESTAMP,
        UNIQUE(username, item)
    )
""")
conn.commit()
conn.close()

# Define items and rotating reward
item_options = ["Wood", "Bacon", "Stone", "Iron", "Water"]
current_reward = random.choice(item_options)

# Shuffle the reward
def shuffle_reward():
    global current_reward
    current_reward = random.choice(item_options)
    logging.info(f"Next reward shuffled to: {current_reward}")

# Award items to users who reach engagement goals
def award_item(username):
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (username, item, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(username, item) DO UPDATE SET quantity = quantity + 1
    """, (username, current_reward))
    conn.commit()
    conn.close()
    logging.info(f"[Award] {username} received 1 '{current_reward}' as a reward.")

# Log the current state of the database tables
def log_database_state():
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    logging.info("[Database] Current engagements:")
    cursor.execute("SELECT * FROM engagements")
    for engagement in cursor.fetchall():
        logging.info(engagement)

    logging.info("[Database] Current inventory:")
    cursor.execute("SELECT * FROM inventory")
    for item in cursor.fetchall():
        logging.info(item)

    conn.close()

class TwitterBot:
    def __init__(self):
        self.twitter_api_v2 = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        self.llm = ChatOpenAI(temperature=0.8, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')
        self.twitter_me_id = self.get_me_id()

    # Retrieves the authenticated bot's user ID
    def get_me_id(self):
        return self.twitter_api_v2.get_me().data.id

    # Get the author's username from a mention
    def get_author_username(self, mention):
        try:
            user_data = self.twitter_api_v2.get_user(id=mention.author_id, user_fields=["username"])
            return user_data.data.username
        except Exception as e:
            logging.error(f"Failed to fetch username for mention ID {mention.id}: {e}")
            return "anonymous"

    # Generate response using language model
    def generate_response(self, tweet_text):
        system_template = """
        You are the reincarnated spirit of a Minecraft Pig, a meme character with strong opinions on gaming, memecoins, and technology.
        RESPONSE FORMAT:
        - Keep responses short (200 characters max).
        - Mention $PIG occasionally.
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
        
        final_prompt = chat_prompt.format_prompt(text=tweet_text).to_messages()
        response = self.llm(final_prompt).content
        return response[:280]

    # Respond to a mention
    def respond_to_mention(self, mention):
        tweet_id = mention.id
        username = self.get_author_username(mention)
        logging.info(f"Username extracted: {username}")

        if "#pigID" in mention.text.lower():
            tagged_usernames = [user["username"] for user in mention.entities["mentions"] if user["username"] != username]
            if tagged_usernames:
                target_username = tagged_usernames[0]
                logging.info(f"Running consistency analysis for tagged user: @{target_username}")
                reply_text = self.run_consistency_analysis(target_username)
                self.twitter_api_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
                return
            logging.info("No tagged username found for #pigID analysis.")
        
        elif "#pigme" in mention.text.lower():
            show_inventory(username, tweet_id)
        else:
            response_text = self.generate_response(mention.text)
            full_response = f"@{username}, {response_text}"
            self.twitter_api_v2.create_tweet(text=full_response, in_reply_to_tweet_id=tweet_id)
            award_item(username)
            logging.info(f"Responded to mention with: {full_response}")

    # Consistency analysis
    def run_consistency_analysis(self, target_username):
        tweets = self.fetch_user_tweets(target_username)
        tickers = self.extract_tickers(tweets)
        consistency_score, ticker_analysis = analyze_tickers_with_market_data(tickers)

        reply_text = f"Consistency Score for @{target_username}: {consistency_score:.2f}\nTop Tickers:\n"
        for ticker, details in ticker_analysis.items():
            reply_text += f"{ticker}: {details['mentions']} mentions\n"
            for idx, entry in enumerate(details["entries"][:3], start=1):
                reply_text += (
                    f"  Entry {idx}: Price: ${entry['price_usd']}, "
                    f"Liquidity: ${entry['liquidity_usd']}, Market Cap: ${entry['market_cap']}, "
                    f"FDV: ${entry['fdv']}\n"
                )
        return reply_text[:280]  # Truncate to 280 characters for Twitter

    # Fetch tweets from a user
    def fetch_user_tweets(self, username):
        tweets = self.twitter_api_v2.get_users_tweets(id=username, max_results=100)
        return [tweet.text for tweet in tweets.data]

    # Extract tickers from tweets
    def extract_tickers(self, tweets):
        ticker_pattern = re.compile(r'\$[A-Za-z0-9]+')
        return [ticker for tweet in tweets for ticker in ticker_pattern.findall(tweet)]

# Analyze tickers using Dexscreener data
def analyze_tickers_with_market_data(tickers):
    ticker_counts = Counter(tickers)
    ticker_analysis = {}
    
    for ticker, mentions in ticker_counts.items():
        response = requests.get(f"{DEXSCREENER_SEARCH_URL}?q={ticker}")
        if response.status_code == 200:
            data = response.json()
            entries = [
                {
                    "price_usd": pair.get("priceUsd"),
                    "liquidity_usd": pair["liquidity"].get("usd", 0),
                    "market_cap": pair.get("marketCap", 0),
                    "fdv": pair.get("fdv", 0)
                }
                for pair in data.get("pairs", [])[:3]
            ]
            ticker_analysis[ticker] = {
                "mentions": mentions,
                "entries": entries
            }
        else:
            logging.error(f"Failed to fetch data for ticker {ticker} from Dexscreener")

    total_mentions = sum(ticker_counts.values())
    most_mentioned_ticker = max(ticker_counts, key=ticker_counts.get)
    consistency_score = ticker_counts[most_mentioned_ticker] / total_mentions if total_mentions else 0

    return consistency_score, ticker_analysis

# Show inventory
def show_inventory(username, tweet_id):
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT last_checked FROM inventory WHERE username = ?", (username,))
    result = cursor.fetchone()
    now = datetime.utcnow()
    
    if result and result[0] and now < datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        remaining_time = (datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24)) - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes = remainder // 60
        response = f"@{username}, check your inventory again in {hours} hours and {minutes} minutes."
    else:
        cursor.execute("SELECT item, quantity FROM inventory WHERE username = ?", (username,))
        inventory = cursor.fetchall()
        inventory_message = ", ".join([f"{item}: {qty}" for item, qty in inventory]) if inventory else "No items"
        response = f"@{username}, here’s your current inventory: {inventory_message}"
        cursor.execute("UPDATE inventory SET last_checked = ? WHERE username = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), username))
    
    conn.commit()
    conn.close()
    
    bot.twitter_api_v2.create_tweet(text=response, in_reply_to_tweet_id=tweet_id)
    logging.info(f"Inventory check complete for @{username}. Inventory: {inventory_message if inventory else 'No items'}")

# Scheduling tasks in separate threads
def run_mentions_check():
    while True:
        bot.check_mentions_for_replies()
        time.sleep(2700)  # Run every 45 minutes

bot = TwitterBot()
shuffle_reward()  # Set initial reward rotation

# Start mention check and engagement check in separate threads
threading.Thread(target=run_mentions_check, daemon=True).start()
schedule.every().hour.do(check_engagements)

while True:
    schedule.run_pending()
    time.sleep(1)
