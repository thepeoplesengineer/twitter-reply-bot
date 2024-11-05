from bot.twitter_bot import TwitterBot
from utils.logging_config import setup_logging
from utils.db import initialize_tweet_data  # New function to handle tweet DB setup and scheduling
from utils.rewards_service import shuffle_reward
from utils.schedule_tasks import check_engagements, post_random_tweet

import schedule
import threading
import time
import logging

def run_mentions_check(bot):
    """Function to repeatedly check mentions every 45 minutes."""
    while True:
        bot.respond_to_mentions()
        time.sleep(2700)  # Run every 45 minutes

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Initialize databases and schedule tweet updates
    initialize_tweet_data()  # Replaces individual calls for DB setup and tweet scheduling

    # Initialize bot and post random tweets
    bot = TwitterBot()
    shuffle_reward()  # Set initial reward rotation
    post_random_tweet(bot)  # Schedule random tweets

    # Start mention checking in a separate thread
    threading.Thread(target=run_mentions_check, args=(bot,), daemon=True).start()

    # Schedule engagement checks every hour
    schedule.every().hour.do(check_engagements)

    # Main loop to run all scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(1)


