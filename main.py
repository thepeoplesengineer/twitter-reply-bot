# main.py

from bot.twitter_bot import TwitterBot
from utils.logging_config import setup_logging
from utils.db import setup_database
from utils.reward_utils import shuffle_reward
import schedule
import threading
import time

def run_mentions_check():
    while True:
        bot.check_mentions_for_replies()
        time.sleep(2700)  # Run every 45 minutes

if __name__ == "__main__":
    setup_logging()
    setup_database()
    bot = TwitterBot()
    shuffle_reward()  # Set initial reward rotation

    # Start mention check and engagement check in separate threads
    threading.Thread(target=run_mentions_check, daemon=True).start()
    schedule.every().hour.do(check_engagements)

    # Run scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(1)
