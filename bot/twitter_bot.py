import tweepy
from config.config import TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, TWITTER_BEARER_TOKEN
from utils.logging_config import logging
from bot.mention_handler import handle_mention


class TwitterBot:
    def __init__(self):
        self.twitter_api_v1 = tweepy.API(tweepy.OAuth1UserHandler(
            TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
        ))
        self.twitter_api_v2 = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                                            consumer_key=TWITTER_API_KEY,
                                            consumer_secret=TWITTER_API_SECRET,
                                            access_token=TWITTER_ACCESS_TOKEN,
                                            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                                            wait_on_rate_limit=True)
        self.twitter_me_id = self.get_me_id()

    def get_me_id(self):
        """Retrieve the bot's Twitter user ID."""
        return self.twitter_api_v2.get_me().data.id

    def respond_to_mentions(self):
        """Fetch new mentions and respond to them."""
        logging.info("Checking for new mentions.")
        mentions = self.twitter_api_v2.get_users_mentions(id=self.twitter_me_id)
        for mention in mentions.data:
            handle_mention(mention, self.twitter_api_v2)
