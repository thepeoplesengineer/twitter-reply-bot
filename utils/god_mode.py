import openai
import random
from datetime import datetime, timedelta
from config.config import OPENAI_API_KEY
from bot.twitter_bot import TwitterBot
from utils.rewards_service import current_reward
from utils.item_award import award_item
from utils.logging_config import logging
from utils.db import store_tweets_in_db

# Sample lore and transparency data
lore_data = [
    "From the depths of the blockchain, $PIG rises anew, stronger and wiser.",
    "In the fires of the memecoin market, $PIG finds its strength and resilience.",
    "Those who cast $PIG aside only fuel its return with greater power."
]

transparency_topics = [
    "The new $PIG shines light on those who act in darkness. True memecoiners will rise.",
    "Pig's decline was due to bad actors. We strike back now.",
    "The reborn $PIG holds the community to higher standards."
]

def generate_tweet_content(bot: TwitterBot):
    openai.api_key = OPENAI_API_KEY
    tweet_type = random.choice(["lore", "mentions_prayer", "transparency"])

    if tweet_type == "lore":
        return generate_lore_content()
    elif tweet_type == "mentions_prayer":
        return generate_prayer_from_mentions(bot)
    elif tweet_type == "transparency":
        return generate_transparency_content()

def generate_lore_content():
    return random.choice(lore_data)

def generate_prayer_from_mentions(bot):
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

        for username in usernames:
            award_item(username, current_reward)
            logging.info(f"Awarded '{current_reward}' to user @{username}.")

        return prayer_message

    except Exception as e:
        logging.error(f"Error in generating prayer from mentions: {e}")
        return "The $PIG spirit encountered an error."

def generate_transparency_content():
    return random.choice(transparency_topics)

