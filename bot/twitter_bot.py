import tweepy
import os
from config.config import TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, TWITTER_BEARER_TOKEN
from utils.logging_config import logging
from bot.mention_handler import handle_mention

REPLIED_MENTIONS_FILE = "replied_mentions.txt"

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
        self.replied_mentions = self.load_replied_mentions()  # Load replied mentions on initialization

    def get_me_id(self):
        """Retrieve the bot's Twitter user ID."""
        try:
            user_id = self.twitter_api_v2.get_me().data.id
            logging.info(f"Retrieved bot's user ID: {user_id}")
            return user_id
        except Exception as e:
            logging.error(f"Failed to retrieve bot's user ID: {e}")
            return None

    def load_replied_mentions(self):
        """Load replied mention IDs from a file to avoid duplicate replies."""
        if not os.path.exists(REPLIED_MENTIONS_FILE):
            return set()
        with open(REPLIED_MENTIONS_FILE, "r") as file:
            return set(line.strip() for line in file)

    def save_replied_mention(self, mention_id):
        """Save a replied mention ID to avoid duplicate replies."""
        with open(REPLIED_MENTIONS_FILE, "a") as file:
            file.write(f"{mention_id}\n")
        logging.info(f"Saved replied mention ID: {mention_id}")

    def respond_to_mentions(self):
        """Fetch new mentions and respond to them."""
        logging.info("Checking for new mentions.")
        try:
            mentions = self.twitter_api_v2.get_users_mentions(id=self.twitter_me_id)
            if not mentions.data:
                logging.info("No new mentions found.")
                return

            for mention in mentions.data:
                mention_id = mention.id
                if mention_id not in self.replied_mentions:
                    logging.info(f"Handling mention from @{mention.author.username} (ID: {mention_id})")
                    handle_mention(mention, self.twitter_api_v2)
                    self.save_replied_mention(mention_id)
                    self.replied_mentions.add(mention_id)
                else:
                    logging.info(f"Already responded to mention ID {mention_id}, skipping.")
        except Exception as e:
            logging.error(f"Error while responding to mentions: {e}")

