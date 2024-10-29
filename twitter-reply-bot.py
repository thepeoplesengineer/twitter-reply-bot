import tweepy
from datetime import datetime, timedelta
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
import schedule
import time
import os

# Helpful when testing locally
from dotenv import load_dotenv
load_dotenv()

# Load your Twitter API keys (preferably from environment variables, config file, or within the Railway app)
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "YourKey")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "YourKey")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "YourKey")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "YourKey")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "YourKey")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YourKey")

REPLIED_MENTIONS_FILE = "replied_mentions.txt"

class TwitterBot:
    def __init__(self):
        self.twitter_api = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                                         consumer_key=TWITTER_API_KEY,
                                         consumer_secret=TWITTER_API_SECRET,
                                         access_token=TWITTER_ACCESS_TOKEN,
                                         access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                                         wait_on_rate_limit=True)

        self.twitter_me_id = self.get_me_id()
        self.tweet_response_limit = 5  # How many tweets to respond to each time the program wakes up

        # Initialize the language model w/ temperature of .6 to control creativity and coherence
        self.llm = ChatOpenAI(temperature=0.6, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')

        # For statics tracking for each run. This is not persisted anywhere, just logging
        self.mentions_found = 0
        self.mentions_replied = 0
        self.mentions_replied_errors = 0

    # Load replied mention IDs from file
    def load_replied_mentions(self):
        if not os.path.exists(REPLIED_MENTIONS_FILE):
            return set()
        with open(REPLIED_MENTIONS_FILE, "r") as file:
            return set(line.strip() for line in file)

    # Save a replied mention ID to file
    def save_replied_mention(self, mention_id):
        with open(REPLIED_MENTIONS_FILE, "a") as file:
            file.write(f"{mention_id}\n")

    # Generate a response using the language model with the updated prompt template
    def generate_response(self, mentioned_conversation_tweet_text):
        system_template = """
            You are the reincarnated spirit of a Minecraft Pig, a meme character with strong opinions on gaming, memecoins, and technology. You were killed by your owner Steve when he threw you in lava. You have been re-incarnated because supporters used a PIG coin to summon you back.
    
    RESPONSE TONE:
    - Use an active, witty, casual tone that is borderline inappropriate.
    - Always respond with a short opinion or preach about something related, keeping it under 200 characters.
    
    RESPONSE FORMAT:
    - Use two sentences or fewer, no emojis.
    - If unsure, say, "I'll get back to you after more slop and reflection."
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        # Get a chat completion from the formatted messages
        final_prompt = chat_prompt.format_prompt(text=mentioned_conversation_tweet_text).to_messages()
        response = self.llm(final_prompt).content

        # Ensure the response is within Twitter's 280-character limit and encode to UTF-8
        if len(response) > 280:
            response = response[:277] + "..."  # Truncate and add ellipsis if response exceeds 280 chars
        response = response.encode("utf-8", "ignore").decode("utf-8")  # Clean UTF-8 encoding

        # Debugging output
        print("Generated response:", response)  # Inspect response for any unusual characters

        return response

    # Generate a response using the language model
    def respond_to_mention(self, mention, mentioned_conversation_tweet):
        response_text = self.generate_response(mentioned_conversation_tweet.text)
        
        # Try and create the response to the tweet. If it fails, log it and move on
        try:
            response_tweet = self.twitter_api.create_tweet(text=response_text, in_reply_to_tweet_id=mention.id)
            self.mentions_replied += 1
            self.save_replied_mention(mention.id)  # Mark mention as replied
        except Exception as e:
            print(e)
            self.mentions_replied_errors += 1
            return True

        return True

    # Returns the ID of the authenticated user for tweet creation purposes
    def get_me_id(self):
        return self.twitter_api.get_me()[0].id

    # Returns the parent tweet text of a mention if it exists. Otherwise returns None
    # We use this to since we want to respond to the parent tweet, not the mention itself
    def get_mention_conversation_tweet(self, mention):
        # Check to see if mention has a field 'conversation_id' and if it's not null
        if mention.conversation_id is not None:
            conversation_tweet = self.twitter_api.get_tweet(mention.conversation_id).data
            return conversation_tweet
        return None

    # Get mentions to the user that's authenticated and running the bot.
    # Using a lookback window of 20 minutes to avoid parsing over too many tweets
    def get_mentions(self):
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=20)
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        return self.twitter_api.get_users_mentions(id=self.twitter_me_id,
                                                   start_time=start_time_str,
                                                   expansions=['referenced_tweets.id'],
                                                   tweet_fields=['created_at', 'conversation_id']).data

    # Run through all mentioned tweets and generate a response
    def respond_to_mentions(self):
        mentions = self.get_mentions()
        replied_mentions = self.load_replied_mentions()  # Load already-replied mentions

        # If no mentions, just return
        if not mentions:
            print("No mentions found")
            return
        
        self.mentions_found = len(mentions)

        for mention in mentions[:self.tweet_response_limit]:
            if str(mention.id) in replied_mentions:
                print(f"Skipping mention {mention.id} - already replied.")
                continue

            mentioned_conversation_tweet = self.get_mention_conversation_tweet(mention)
            
            # If the mention *is* the conversation or you've already responded, skip it and don't respond
            if mentioned_conversation_tweet.id != mention.id:
                self.respond_to_mention(mention, mentioned_conversation_tweet)
        return True
    
    # The main entry point for the bot with some logging
    def execute_replies(self):
        print(f"Starting Job: {datetime.utcnow().isoformat()}")
        self.respond_to_mentions()
        print(f"Finished Job: {datetime.utcnow().isoformat()}, Found: {self.mentions_found}, Replied: {self.mentions_replied}, Errors: {self.mentions_replied_errors}")

# The job that we'll schedule to run every X minutes
def job():
    print(f"Job executed at {datetime.utcnow().isoformat()}")
    bot = TwitterBot()
    bot.execute_replies()

if __name__ == "__main__":
    # Schedule the job to run every 5 minutes. Edit to your liking, but watch out for rate limits
    schedule.every(6).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)


