# utils/twitter_utils.py
import tweepy

def fetch_user_tweets(twitter_api, user_id, count=100):
    tweets = twitter_api.get_users_tweets(id=user_id, max_results=count)
    return [tweet.text for tweet in tweets.data]
