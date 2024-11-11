import random
import logging
from utils.item_award import award_item



# Define items and rotating reward
item_options = ["Wood", "Bacon", "Stone", "Iron", "Water"]
current_reward = random.choice(item_options)  # Start with a random reward
ENGAGEMENT_TOTAL_TARGET = 3  # Engagement threshold for reward distribution
goal_achieved_tweets = set()  # Track tweets that already met the goal

def shuffle_reward():
    global current_reward
    current_reward = random.choice(item_options)
    logging.info(f"[REWARD ROTATION] Next reward shuffled to: {current_reward}")

def check_engagements(bot):
    logging.info("[ENGAGEMENT CHECK] Checking engagements on bot's recent tweets.")
    bot_tweets = bot.twitter_api_v2.get_users_tweets(id=bot.twitter_me_id, max_results=10)

    for tweet in bot_tweets.data:
        tweet_id = tweet.id
        if tweet_id in goal_achieved_tweets:
            continue  # Skip tweets that already reached engagement goals

        try:
            # Fetch engagement metrics for the tweet
            tweet_metrics = bot.twitter_api_v2.get_tweet(tweet_id, tweet_fields="public_metrics").data["public_metrics"]
            total_engagements = tweet_metrics["like_count"] + tweet_metrics["retweet_count"] + tweet_metrics["reply_count"]
            logging.info(f"[ENGAGEMENT COUNT] Tweet {tweet_id} total engagements: {total_engagements}")

            # Check if total engagements meet or exceed the threshold
            if total_engagements >= ENGAGEMENT_TOTAL_TARGET:
                goal_achieved_tweets.add(tweet_id)  # Mark tweet as rewarded
                logging.info(f"[ENGAGEMENT TARGET MET] Tweet {tweet_id} reached engagement target. Distributing rewards.")
                
                # Distribute rewards to users who engaged with the tweet
                distribute_rewards(tweet_id, bot)
                
                # Shuffle to the next resource
                shuffle_reward()

        except Exception as e:
            logging.error(f"[ERROR] Failed to fetch engagements for tweet {tweet_id}: {e}")

# rewards_service.py

def distribute_rewards_for_goals():
    """Distribute rewards for tweets that met the engagement goal."""
    for tweet_id in list(goal_achieved_tweets):
        distribute_rewards(tweet_id)  # Distribute reward for each flagged tweet
        shuffle_reward()  # Rotate the reward after each distribution
        goal_achieved_tweets.remove(tweet_id)  # Remove or archive once processed


def distribute_rewards(tweet_id, bot):
    """
    Award the current resource to each user who engaged with the specified tweet.
    """
    try:
        # Retrieve the list of users who engaged with the tweet
        tweet_engagements = bot.twitter_api_v2.get_tweet(tweet_id, expansions="author_id", tweet_fields="public_metrics")

        # Collect usernames of users who engaged with the tweet
        engaged_users = set()
        for engagement in tweet_engagements.includes["users"]:
            username = engagement.username
            engaged_users.add(username)

        # Award the current reward to each user who engaged
        for username in engaged_users:
            award_item(username, current_reward)  # Pass current_reward
            logging.info(f"[AWARD ITEM] Awarded '{current_reward}' to user @{username} for engagement on tweet {tweet_id}")
            
    except Exception as e:
        logging.error(f"[ERROR] Unable to distribute rewards for tweet {tweet_id}: {e}")

