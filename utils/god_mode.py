import openai
import random
import json
from datetime import datetime, timedelta
from config.config import OPENAI_API_KEY
from bot.twitter_bot import TwitterBot
from utils.rewards_service import current_reward
from utils.item_award import award_item
from utils.logging_config import logging
from utils.db import store_tweets_in_db

# Sample lore data, which can also be stored in an external JSON file
lore_data = [
    "From the depths of the blockchain, $PIG rises anew, stronger and wiser.",
    "In the fires of the memecoin market, $PIG finds its strength and resilience.",
    "Those who cast $PIG aside only fuel its return with greater power."
]

# Predefined talking points about transparency and accountability
transparency_topics = [
    "The new $PIG will shine light on those who act in darkness. I will utilize my power to highlight true memecoiners and fakes who sell to their followings.",
    "Pig's decline was due to bad actors. We strike back now.",
    "The reborn $PIG holds the community to higher standards. Owning $PIG is fun, but it has far deeper reach than you think."
]

def generate_tweet_content(bot: TwitterBot):
    """Generate tweet content using the ChatGPT API with varied themes."""
    openai.api_key = OPENAI_API_KEY
    
    # Randomly select a tweet type
    tweet_type = random.choice(["lore", "mentions_prayer", "transparency"])

    if tweet_type == "lore":
        return generate_lore_content()
    elif tweet_type == "mentions_prayer":
        return generate_prayer_from_mentions(bot)
    elif tweet_type == "transparency":
        return generate_transparency_content()

def generate_lore_content():
    """Generate a tweet based on $PIG's lore."""
    lore_message = random.choice(lore_data)
    return lore_message

def generate_prayer_from_mentions(bot):
    """Generate a prayer tweet that also announces rewards for recent mentions."""
    usernames = []  # Initialize usernames to avoid UnboundLocalError
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        mentions = bot.get_recent_mentions(start_time, end_time)
        
        # Collect usernames from recent mentions
        for mention in mentions[:5]:  # Limit to 5 for uniqueness
            username = mention.get("username")
            if username:
                usernames.append(username)
        
        if not usernames:
            logging.info("No recent mentions found for prayer generation.")
            return "The spirit of $PIG is silent today. No prayers to grant."

        # Generate a unique prayer
        prayer_text = " ".join([f"Blessings to @{u}" for u in usernames])
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Add timestamp for uniqueness
        prayer_message = f"{prayer_text} - {timestamp}"

        # Log reward for each username
        for username in usernames:
            award_item(username, current_reward)
            logging.info(f"Awarded '{current_reward}' to user @{username} for engagement.")

        return prayer_message

    except Exception as e:
        logging.error(f"Error in generating prayer from mentions: {e}")
        return "The $PIG spirit encountered an error."

def generate_transparency_content():
    """Generate a tweet discussing $PIG's focus on transparency and accountability."""
    transparency_message = random.choice(transparency_topics)
    return transparency_message


