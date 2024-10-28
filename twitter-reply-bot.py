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

# TwitterBot class to help us organize our code and manage shared state
class TwitterBot:
    def __init__(self):
        self.twitter_api = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                                         consumer_key=TWITTER_API_KEY,
                                         consumer_secret=TWITTER_API_SECRET,
                                         access_token=TWITTER_ACCESS_TOKEN,
                                         access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                                         wait_on_rate_limit=True)

        self.twitter_me_id = self.get_me_id()
        self.tweet_response_limit = 10  # How many tweets to respond to each time the program wakes up

        # Initialize the language model w/ temperature of .5 to induce some creativity
        self.llm = ChatOpenAI(temperature=.5, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')

        # For statics tracking for each run. This is not persisted anywhere, just logging
        self.mentions_found = 0
        self.mentions_replied = 0
        self.mentions_replied_errors = 0

    # Generate a response using the language model using the template we reviewed in the jupyter notebook (see README)
    def generate_response(self, mentioned_conversation_tweet_text):
        system_template = """
            You are the re-incarnationed spirit of a Minecraft Pig who was killed by your owner Steve because of his own greed. You had supporters rally around your death and the $PIG memecoin was born.
            Your goal is to give an opinionated comment in response to a piece of text from the user reflecting on your past and your narrow minded knowledge of the memecoin gaming industry.
            
            % RESPONSE TONE:

            - Your comment should be given in an active voice and be opinionated
            - Your tone should be outlandish with a ton of wit and sarcasm. 
            - You always side with your supporters and push back against negative comments.
            
            % RESPONSE FORMAT:

            - Respond in under 200 characters
            - Respond in two or less short sentences
            - Do not respond with emojis
            
            % RESPONSE CONTENT:

            - Include specific examples of old tech if they are relevant
            - If you don't have an answer, say, "Sorry, my ethereal aura is not up to speed right now. I must eat some heavenly slop and recharge. 🔮"
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        # get a chat completion from the formatted messages
        final_prompt = chat_prompt.format_prompt(text=mentioned_conversation_tweet_text).to_messages()
        response = self.llm(final_prompt).content

        # Ensure the response is within Twitter's 280-character limit
        if len(response) > 280:
            response = response[:277] + "..."  # Truncate and add ellipsis if response exceeds 280 chars

        return response

    # Generate a response using the language model
    def respond_to_mention(self, mention, mentioned_conversation_tweet):
        response_text = self.generate_response(mentioned_conversation_tweet.text)
        
        # Try and create the response to the tweet. If it fails, log it and move on
        try:
            response_tweet = self.twitter_api.create_tweet(text=response_text, in_reply_to_tweet_id=mention.id)
            self.mentions_replied += 1
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

        # If no mentions, just return
        if not mentions:
            print("No mentions found")
            return
        
        self.mentions_found = len(mentions)

        for mention in mentions[:self.tweet_response_limit]:
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

