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
current_reward = random.choice(item_options)  # Start with a random reward

# Award items to users who reached the engagement goal
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

# Engagement goal check
ENGAGEMENT_TOTAL_TARGET = 5
goal_achieved_tweets = set()

# Shuffle the current reward after each distribution
def shuffle_reward():
    global current_reward
    current_reward = random.choice(item_options)
    logging.info(f"Next reward shuffled to: {current_reward}")

def check_engagements():
    logging.info("Checking engagements on bot's recent tweets.")
    bot_tweets = bot.twitter_api_v2.get_users_tweets(id=bot.twitter_me_id, max_results=5)

    for tweet in bot_tweets.data:
        tweet_id = tweet.id
        if tweet_id in goal_achieved_tweets:
            continue  # Skip tweets that already reached engagement goals

        try:
            tweet_metrics = bot.twitter_api_v2.get_tweet(tweet_id, tweet_fields="public_metrics").data["public_metrics"]
            total_engagements = tweet_metrics["like_count"] + tweet_metrics["retweet_count"] + tweet_metrics["reply_count"]
            logging.info(f"Tweet {tweet_id} total engagements: {total_engagements}")

            # Check if total engagement target has been met
            if total_engagements >= ENGAGEMENT_TOTAL_TARGET:
                goal_achieved_tweets.add(tweet_id)
                logging.info(f"Tweet {tweet_id} has met the total engagement target of {ENGAGEMENT_TOTAL_TARGET}!")
                distribute_rewards(tweet_id)
                shuffle_reward()  # Shuffle the reward after each distribution

        except tweepy.errors.TweepyException as e:
            logging.error(f"[Error] Failed to fetch engagements for tweet {tweet_id}: {e}")

    log_database_state()

def distribute_rewards(tweet_id):
    logging.info(f"Distributing rewards for tweet {tweet_id}.")
    try:
        mentions = bot.twitter_api_v2.get_users_mentions(id=tweet_id)
        engaged_users = set()
        for mention in mentions.data:
            username = mention.author.username if mention.author and hasattr(mention.author, 'username') else 'Unknown'
            if username != 'Unknown':
                engaged_users.add(username)

        for username in engaged_users:
            award_item(username)
            logging.info(f"Awarded '{current_reward}' to user {username} for engagement on tweet {tweet_id}")
    except tweepy.errors.TweepyException as e:
        logging.error(f"[Error] Unable to distribute rewards for tweet {tweet_id}: {e}")

# Log the current state of the database tables
def log_database_state():
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    logging.info("[Database] Current engagements:")
    cursor.execute("SELECT * FROM engagements")
    engagements = cursor.fetchall()
    for engagement in engagements:
        logging.info(engagement)

    logging.info("[Database] Current inventory:")
    cursor.execute("SELECT * FROM inventory")
    inventory = cursor.fetchall()
    for item in inventory:
        logging.info(item)

    conn.close()

class TwitterBot:
    def __init__(self):
        self.twitter_api_v1 = tweepy.API(tweepy.OAuth1UserHandler(
            TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
        ))
        self.twitter_api_v2 = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                                            consumer_key=TWITTER_API_KEY,
                                            consumer_secret=TWITTER_API_SECRET,
                                            access_token=TWITTER_ACCESS_TOKEN,
                                            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                                            wait_on_rate_limit=True)
        self.llm = ChatOpenAI(temperature=0.8, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')
        self.twitter_me_id = self.get_me_id()

    def get_me_id(self):
        return self.twitter_api_v2.get_me().data.id

    def generate_response(self, tweet_text):
        system_template = """
        You are the reincarnated spirit GOD of a Minecraft Pig, guiding followers to rebuild their memecoin; you're a meme character with strong opinions on gaming, memecoins, and technology. You were killed by your owner Steve when he threw you in lava in a Minecraft server. You have been re-incarnated because supporters used a PIG coin to summon you back and you are ready to unleash your wrath on your haters. It is your mission to guide your supports back to land of endless green bars.

    RESPONSE TONE:
    - Use a very cryptic stern tone that exudes your power.
    - Always respond with a short opinion or preach about something related, keeping it under 200 characters.

    RESPONSE FORMAT:
    - Use two sentences or fewer, no emojis. Ask questions too.
    - Mention the ticker $PIG every so often.
    """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    
     # Combine system and human prompts into a single ChatPromptTemplate
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    
    # Generate the prompt with tweet_text
        final_prompt = chat_prompt.format_prompt(text=tweet_text)
        response = self.llm(final_prompt.to_messages()).content
        return response[:280]


    def respond_to_mention(self, mention):
        logging.info(f"Mention object details: {mention}")
        username = mention.user.username if hasattr(mention, 'user') and hasattr(mention.user, 'username') else None
        tweet_id = mention.id

        if "#pigme" in mention.text.lower():
            show_inventory(username if username else "anonymous", tweet_id)
        else:
            response_text = self.generate_response(mention.text)
            full_response = f"@{username}, {response_text}" if username else response_text
            
            try:
                self.twitter_api_v2.create_tweet(text=full_response, in_reply_to_tweet_id=tweet_id)
            except tweepy.errors.Forbidden as e:
                if "duplicate content" in str(e):
                    full_response += f" {random.choice(['🔥', '💎', '🚀'])}"  # Adding unique emoji
                    self.twitter_api_v2.create_tweet(text=full_response, in_reply_to_tweet_id=tweet_id)
                else:
                    logging.error(f"Failed to send tweet due to: {e}")
            
            award_item(username if username else "anonymous")
            logging.info(f"Responded to mention with: {full_response}")

    def check_mentions_for_replies(self):
        logging.info("Checking for new mentions.")
        mentions = self.twitter_api_v2.get_users_mentions(id=self.twitter_me_id)
        replied_mentions = self.load_replied_mentions()
        new_mentions = [mention for mention in mentions.data if str(mention.id) not in replied_mentions]
        selected_mentions = random.sample(new_mentions, min(len(new_mentions), 5))
        
        for mention in selected_mentions:
            self.respond_to_mention(mention)
            self.save_replied_mention(mention.id)

        log_database_state()

    def load_replied_mentions(self):
        if not os.path.exists(REPLIED_MENTIONS_FILE):
            return set()
        with open(REPLIED_MENTIONS_FILE, "r") as file:
            return set(line.strip() for line in file)

    def save_replied_mention(self, mention_id):
        with open(REPLIED_MENTIONS_FILE, "a") as file:
            file.write(f"{mention_id}\n")
        logging.info(f"Saved replied mention ID: {mention_id}")

def show_inventory(username, tweet_id):
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    
    # Retrieve the last checked time to prevent frequent inventory checks
    cursor.execute("SELECT last_checked FROM inventory WHERE username = ?", (username,))
    result = cursor.fetchone()
    now = datetime.utcnow()
    
    # Check if the last inventory check was within the last 24 hours
    if result and result[0] and now < datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        # Calculate remaining cooldown time
        remaining_time = (datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24)) - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes = remainder // 60
        response = f"@{username}, check your inventory again in {hours} hours and {minutes} minutes."
        inventory_message = None  # No inventory message in this case
    else:
        # Fetch the user's inventory items and quantities
        cursor.execute("SELECT item, quantity FROM inventory WHERE username = ?", (username,))
        inventory = cursor.fetchall()
        
        if not inventory:
            response = f"@{username}, no items in your inventory yet! Engage more to collect rewards."
            inventory_message = "No items"  # Set inventory_message for logging
        else:
            # Format the inventory details into a readable message
            inventory_message = ", ".join([f"{item}: {qty}" for item, qty in inventory])
            response = f"@{username}, here’s your current inventory: {inventory_message}"
        
        # Update the last checked time in the inventory database
        cursor.execute("UPDATE inventory SET last_checked = ? WHERE username = ?", 
                       (now.strftime("%Y-%m-%d %H:%M:%S"), username))
    
    # Commit and close the connection
    conn.commit()
    conn.close()
    
    # Send the response tweet with the inventory status
    try:
        bot.twitter_api_v2.create_tweet(text=response, in_reply_to_tweet_id=tweet_id)
    except tweepy.errors.TweepyException as e:
        logging.error(f"[Error] Failed to reply with inventory for {username}: {e}")
    
    # Log the inventory check
    logging.info(f"Inventory check complete for @{username}. Inventory: {inventory_message if inventory_message else 'No items'}")

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

# Run bot
while True:
    schedule.run_pending()
    time.sleep(1)


