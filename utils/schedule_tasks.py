import logging
import tweepy
import schedule
import random
from datetime import datetime, timedelta
from utils.rewards_service import distribute_rewards, shuffle_reward
from bot.twitter_bot import TwitterBot
from utils.god_mode import generate_tweet_content
from utils.db import fetch_and_store_all_tweets

# Define engagement target and achieved goals set
ENGAGEMENT_TOTAL_TARGET = 5
goal_achieved_tweets = set()

def check_engagements():
    bot = TwitterBot()
    try:
        bot_tweets = bot.twitter_api_v2.get_users_tweets(id=bot.twitter_me_id, max_results=5)
        for tweet in bot_tweets.data:
            tweet_id = tweet.id
            if tweet_id not in goal_achieved_tweets:
                metrics = bot.twitter_api_v2.get_tweet(tweet_id, tweet_fields="public_metrics").data["public_metrics"]
                total_engagements = metrics["like_count"] + metrics["retweet_count"] + metrics["reply_count"]
                logging.info(f"Tweet {tweet_id} total engagements: {total_engagements}")

                if total_engagements >= ENGAGEMENT_TOTAL_TARGET:
                    goal_achieved_tweets.add(tweet_id)
                    logging.info(f"Tweet {tweet_id} met engagement target.")
    except tweepy.TweepyException as e:
        logging.error(f"Error fetching engagement data: {e}")

def log_database_state():
    from utils.db import get_all_engagements, get_all_inventory
    logging.info("[Database] Current engagements:")
    for engagement in get_all_engagements():
        logging.info(engagement)
    logging.info("[Database] Current inventory:")
    for item in get_all_inventory():
        logging.info(item)

def post_random_tweet(bot):
    times = sorted([random.randint(0, 24 * 60) for _ in range(3)])
    for minutes in times:
        random_time = (datetime.now().replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()
        schedule.every().day.at(random_time.strftime("%H:%M")).do(post_tweet, bot)
    logging.info(f"Scheduled tweets for: {[random_time.strftime('%H:%M') for minutes in times]}")

def post_tweet(bot):
    content = generate_tweet_content(bot)
    try:
        bot.twitter_api_v2.create_tweet(text=content)
        logging.info(f"Posted tweet: {content}")
    except tweepy.errors.Forbidden as e:
        if "duplicate content" in str(e).lower():
            logging.warning("Duplicate tweet content; tweet not posted.")
        else:
            logging.error(f"Failed to post tweet: {e}")

def update_tweet_database():
    usernames = ["blknoiz06", "MustStopMurad", "notthreadguy"]
    for username in usernames:
        fetch_and_store_all_tweets(username, max_count=8)

# Schedule tasks
schedule.every(8).hours.do(update_tweet_database)
schedule.every().hour.do(check_engagements)



