from bot.twitter_bot import TwitterBot
from utils.logging_config import setup_logging
from utils.db import initialize_tweet_data
from utils.rewards_service import shuffle_reward, distribute_rewards_for_goals
from utils.schedule_tasks import check_engagements
from utils.god_mode import generate_lore_content, generate_prayer_from_mentions, generate_transparency_content, respond_with_quote_tweet

import schedule
import threading
import time
import logging
import random


def run_mentions_check(bot):
    """Function to repeatedly check mentions every 45 minutes."""
    while True:
        bot.respond_to_mentions()
        time.sleep(2700)  # Run every 45 minutes

def generate_tweet_content(bot):
    """Decide on the tweet type and generate content accordingly."""
    tweet_type = random.choice(["lore", "mentions_prayer", "transparency", "quote_tweet"])

    if tweet_type == "lore":
        content = generate_lore_content()
        bot.tweet(content)
        logging.info(f"[LORE TWEET] Tweeted lore content: {content}")
    elif tweet_type == "mentions_prayer":
        content = generate_prayer_from_mentions(bot)
        bot.tweet(content)
        logging.info(f"[PRAYER TWEET] Tweeted mentions prayer: {content}")
    elif tweet_type == "transparency":
        content = generate_transparency_content()
        bot.tweet(content)
        logging.info(f"[TRANSPARENCY TWEET] Tweeted transparency content: {content}")
    elif tweet_type == "quote_tweet":
        respond_with_quote_tweet()  # Handles its own posting and logging
        logging.info("[QUOTE TWEET] Responded with a quote tweet and AI-powered reply")

def post_random_tweet(bot):
    """Wrapper for generate_tweet_content to post a tweet at random intervals."""
    generate_tweet_content(bot)
    # Reschedule this function to run at a random interval (every 3 to 6 hours)
    next_interval = random.randint(3450, 5900)  # Between 3 and 6 hours in seconds
    schedule.every(next_interval).seconds.do(post_random_tweet, bot)
    logging.info(f"[RANDOM TWEET SCHEDULED] Next tweet in {next_interval // 3600} hours.")

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Initialize databases and schedule tweet updates
    initialize_tweet_data()  # Replaces individual calls for DB setup and tweet scheduling

    # Initialize bot and post the first random tweet
    bot = TwitterBot()
    shuffle_reward()  # Set initial reward rotation
    post_random_tweet(bot)  # Schedule the first random tweet

    # Start mention checking in a separate thread
    threading.Thread(target=run_mentions_check, args=(bot,), daemon=True).start()

    # Schedule engagement checks and reward distribution
    schedule.every().hour.do(check_engagements)  # Only checks engagements and flags tweets
    schedule.every().hour.do(distribute_rewards_for_goals)  # Handles reward distribution for flagged tweets

    # Main loop to run all scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(1)



