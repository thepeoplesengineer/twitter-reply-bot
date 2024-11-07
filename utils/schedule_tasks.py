import logging
import tweepy
import schedule
import random
from datetime import datetime, timedelta
from utils.rewards_service import distribute_rewards, shuffle_reward
from utils.item_award import award_item
from bot.twitter_bot import TwitterBot
from utils.god_mode import generate_tweet_content
from utils.db import fetch_and_store_tweets, fetch_and_store_piglore_tweets, get_user_ids

# Define engagement target
ENGAGEMENT_TOTAL_TARGET = 5
goal_achieved_tweets = set()  # Tracks tweets that met engagement goal

def check_engagements():
    """Check recent tweets by the bot for engagement and flag those that meet the target."""
    bot = TwitterBot()
    try:
        bot_tweets = bot.twitter_api_v2.get_users_tweets(id=bot.twitter_me_id, max_results=5)
        for tweet in bot_tweets.data:
            tweet_id = tweet.id
            if tweet_id not in goal_achieved_tweets:
                tweet_metrics = bot.twitter_api_v2.get_tweet(tweet_id, tweet_fields="public_metrics").data["public_metrics"]
                total_engagements = tweet_metrics["like_count"] + tweet_metrics["retweet_count"] + tweet_metrics["reply_count"]
                logging.info(f"Tweet {tweet_id} total engagements: {total_engagements}")

                if total_engagements >= ENGAGEMENT_TOTAL_TARGET:
                    goal_achieved_tweets.add(tweet_id)  # Only add to achieved set
                    distribute_rewards(tweet_id)  # Distribute rewards when goal is met
                    shuffle_reward()  # Rotate reward for the next round
                    logging.info(f"Tweet {tweet_id} met engagement target; rewards distributed and shuffled.")
    except tweepy.TweepyException as e:
        logging.error(f"Error fetching engagement data: {e}")


def log_database_state():
    """Logs the current state of the engagement and inventory databases for debugging."""
    from utils.db import get_all_engagements, get_all_inventory
    logging.info("[Database] Current engagements:")
    for engagement in get_all_engagements():
        logging.info(engagement)
    logging.info("[Database] Current inventory:")
    for item in get_all_inventory():
        logging.info(item)

def post_random_tweet(bot):
    """Schedule three random tweet posts within a 24-hour period."""
    times = sorted([random.randint(0, 24 * 60) for _ in range(3)])  # Random times in minutes from start of the day
    formatted_times = []
    for minutes in times:
        random_time = (datetime.now().replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()
        formatted_times.append(random_time.strftime("%H:%M"))  # For logging
        schedule.every().day.at(random_time.strftime("%H:%M")).do(post_tweet, bot)
    logging.info(f"Scheduled tweets for times: {formatted_times}")

def post_tweet(bot):
    """Generate tweet content and post it using the bot, avoiding duplicates."""
    content = generate_tweet_content(bot)
    try:
        bot.twitter_api_v2.create_tweet(text=content)
        logging.info(f"Posted tweet: {content}")
    except tweepy.errors.Forbidden as e:
        if "duplicate content" in str(e).lower():
            logging.warning("Attempted to post duplicate content; tweet not posted.")
        else:
            logging.error(f"Failed to post tweet: {e}")



# Schedule tasks
schedule.every(8).hours.do(update_tweet_database)
schedule.every().hour.do(check_engagements)

# Main loop to run all scheduled tasks
if __name__ == "__main__":
    logging.info("Starting scheduled tasks...")
    while True:
        schedule.run_pending()
        time.sleep(1)




