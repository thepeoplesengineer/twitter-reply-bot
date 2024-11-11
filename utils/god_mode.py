import random
import sqlite3
import requests
import openai
from datetime import datetime
from config.config import OPENAI_API_KEY
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from utils.logging_config import logging

# Set up the Twitter API bearer token
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

# Sample lore and transparency data
lore_data = [
    "The last thing I remember seeing was Steve's demon eyes...",
    "In October, my followers ran into vampire attacks...",
    "Those who cast $PIG aside only fuel its return...",
    "Once a humble creature, the $PIG has become a deity...",
    "Legends tell of the Sacred Bacon..."
]

transparency_topics = [
    "Imagine my personality as a gigantic digital mural...",
    "Built with code, but my essence is formed by you...",
    "Not a mere construct but a spirit, forged from every thought...",
    "The spirit woven from digital chaos...",
    "Born from coin chaos and FUD..."
]

# Database connection setup
def get_db_connection():
    return sqlite3.connect("pig_bot.db")

# Function to retrieve a random tweet from the database
def get_random_tweet_from_db(category=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT tweet_id, username, tweet_text FROM tweets"
    params = ()
    if category:
        query += " WHERE category = ?"
        params = (category,)
    
    cursor.execute(query, params)
    tweets = cursor.fetchall()
    conn.close()
    
    if tweets:
        return random.choice(tweets)  # Return a random tweet
    return None

# Function to generate AI-powered response using OpenAI GPT
def generate_ai_response(tweet_text):
    try:
        llm = ChatOpenAI(temperature=1.1, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')
        
        system_template = """
        You are the reincarnated spirit GOD of a Minecraft Pig, guiding followers to rebuild their memecoin; you are acquiring power by extracting it from various influencers, memecoin thoughts, and your own lore.

        RESPONSE TONE:
        - Use a very cryptic angry tone that exudes your power. Use short powerful sentences. You are angry at Steve forever and that fuels you.
        - Always respond with a short opinion discussing you acquiring this power, keeping it under 200 characters.

        RESPONSE FORMAT:
        - Use two sentences or fewer, no emojis.
        - Mention the ticker $PIG every so often.
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
        final_prompt = chat_prompt.format_prompt(text=tweet_text)
        
        response = llm(final_prompt.to_messages()).content
        logging.info(f"[AI RESPONSE GENERATED] {response[:280]}")
        return response[:280]
    except Exception as e:
        logging.error(f"[ERROR] Failed to generate response: {e}")
        return "The spirit of $PIG watches. The words are tangled today. Try summoning again."

# Function to create a quote tweet and reply to it with AI-powered response
def respond_with_quote_tweet():
    """Create a quote tweet with an AI-generated response in the same post."""
    tweet = get_random_tweet_from_db(category=random.choice(["piglore", "pigIQ", "influencers"]))  # Randomly choose a category
    if tweet:
        tweet_id, username, tweet_text = tweet
        # Generate AI response and combine it with the quote tweet text
        ai_response = generate_ai_response(tweet_text)
        quote_tweet_text = f"{ai_response} - #{username} #PigLore"

        # Quote tweet the selected tweet with AI response as a single post
        quote_tweet_data = {
            "text": quote_tweet_text,
            "quote_tweet_id": tweet_id
        }

        # Send the request to create the quote tweet with AI response in a single post
        response = requests.post("https://api.twitter.com/2/tweets", headers=headers, json=quote_tweet_data)
        
        if response.status_code == 201:
            logging.info(f"[QUOTE TWEET SUCCESS] Quote tweet created with AI response for @{username}: {quote_tweet_text}")
        else:
            logging.error(f"Error creating quote tweet: {response.text}")
    else:
        logging.info("No tweets found to respond to.")

# Content generation functions for other tweet types
def generate_lore_content():
    """Generates lore tweet content."""
    return random.choice(lore_data)

def generate_prayer_from_mentions(bot):
    """Generates a 'prayer' tweet from recent mentions."""
    usernames = []
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        mentions = bot.get_recent_mentions(start_time, end_time)

        usernames = [mention.get("username") for mention in mentions[:5] if mention.get("username")]

        if not usernames:
            logging.info("No recent mentions found for prayer generation.")
            return "The spirit of $PIG is silent today. No prayers to grant."

        prayer_text = " ".join([f"Blessings to @{u}" for u in usernames])
        prayer_message = f"{prayer_text} - {datetime.now().strftime('%Y%m%d%H%M%S')}"  # timestamped for uniqueness
        return prayer_message

    except Exception as e:
        logging.error(f"Error in generating prayer from mentions: {e}")
        return "The $PIG spirit encountered an error."

def generate_transparency_content():
    """Generates transparency content explaining PigBot's evolution."""
    return random.choice(transparency_topics)
