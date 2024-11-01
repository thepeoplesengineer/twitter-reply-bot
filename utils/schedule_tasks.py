import logging
import tweepy
from utils.reward_utils import distribute_rewards, shuffle_reward
from bot.twitter_bot import TwitterBot

# Define engagement targets and tracking set
ENGAGEMENT_TOTAL_TARGET = 5
goal_achieved_tweets = set()

def check_engagements():
    """Check recent tweets by the bot for engagement and distribute rewards if targets are met."""
    logging.info("Checking engagements on bot's recent tweets.")
    bot_tweets = TwitterBot().twitter_api_v2.get_users_tweets(id=TwitterBot().twitter_me_id, max_results=5)

    for tweet in bot_tweets.data:
        tweet_id = tweet.id
        if tweet_id in goal_achieved_tweets:
            continue  # Skip tweets that already reached engagement goals

        try:
            tweet_metrics = TwitterBot().twitter_api_v2.get_tweet(tweet_id, tweet_fields="public_metrics").data["public_metrics"]
            total_engagements = tweet_metrics["like_count"] + tweet_metrics["retweet_count"] + tweet_metrics["reply_count"]
            logging.info(f"Tweet {tweet_id} total engagements: {total_engagements}")

            # Check if the total engagement target has been met
            if total_engagements >= ENGAGEMENT_TOTAL_TARGET:
                goal_achieved_tweets.add(tweet_id)
                logging.info(f"Tweet {tweet_id} has met the total engagement target of {ENGAGEMENT_TOTAL_TARGET}!")
                distribute_rewards(tweet_id)
                shuffle_reward()  # Shuffle the reward after each distribution

        except tweepy.errors.TweepyException as e:
            logging.error(f"[Error] Failed to fetch engagements for tweet {tweet_id}: {e}")

    # Optional: Log the current state of rewards and engagements
    log_database_state()

def log_database_state():
    """Logs the current state of the engagement and inventory databases for debugging."""
    from utils.db import get_all_engagements, get_all_inventory

    logging.info("[Database] Current engagements:")
    engagements = get_all_engagements()
    for engagement in engagements:
        logging.info(engagement)

    logging.info("[Database] Current inventory:")
    inventory = get_all_inventory()
    for item in inventory:
        logging.info(item)
