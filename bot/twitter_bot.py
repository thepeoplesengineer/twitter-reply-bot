import tweepy
import os
from config.config import TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, TWITTER_BEARER_TOKEN
from utils.logging_config import logging
from bot.mention_handler import handle_mention  
from utils.rewards_service import current_reward
from datetime import datetime




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
        self.replied_mentions = self.load_replied_mentions()

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

    def get_username_by_author_id(self, author_id):
        """Retrieve the username by author ID."""
        try:
            user = self.twitter_api_v2.get_user(id=author_id, user_fields=["username"]).data
            return user.username
        except Exception as e:
            logging.error(f"Failed to retrieve username for author ID {author_id}: {e}")
            return "anonymous"

    def respond_to_mentions(self):
        """Fetch new mentions and respond to them."""
        logging.info("Checking for new mentions.")
        try:
            # Retrieve mentions with author_id expansion
            mentions = self.twitter_api_v2.get_users_mentions(id=self.twitter_me_id, expansions="author_id")
            
            for mention in mentions.data:
                mention_id = mention.id
                
                # Check if we have already replied to this mention
                if mention_id not in self.replied_mentions:
                    # Retrieve username using author_id from includes
                    author_id = mention.author_id
                    username = self.get_username_by_author_id(author_id)
                    
                    logging.info(f"Handling mention from @{username} (ID: {mention_id})")
                    
                    # Handle the mention and add the mention ID to the set
                    handle_mention(mention, self.twitter_api_v2, username, current_reward)
                    self.save_replied_mention(mention_id)
                    self.replied_mentions.add(mention_id)
                else:
                    logging.info(f"Already responded to mention ID {mention_id}, skipping.")
        
        except Exception as e:
            logging.error(f"Error while responding to mentions: {e}", exc_info=True)
    
    def get_recent_mentions(self, start_time, end_time):
        """Fetch mentions within a specific timeframe."""
        try:
            # Pull the latest 100 mentions
            mentions = self.twitter_api_v2.get_users_mentions(id=self.twitter_me_id, max_results=30)
            recent_mentions = []
            for mention in mentions.data:
                # Convert created_at to a datetime object and filter by time frame
                mention_time = datetime.strptime(mention.created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                if start_time <= mention_time <= end_time:
                    recent_mentions.append({"text": mention.text, "created_at": mention_time})
            logging.info(f"Found {len(recent_mentions)} recent mentions within the specified time frame.")
            return recent_mentions
        except Exception as e:
            logging.error(f"Error fetching recent mentions: {e}")
            return []


