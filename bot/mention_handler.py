from dex.dex_analysis import run_consistency_analysis
from utils.item_award import award_item  # Import in mention handler if needed
from utils.logging_config import logging
import requests
import json

from langchain.chat_models import ChatOpenAI

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from config.config import OPENAI_API_KEY
import tweepy  # Import tweepy for direct messaging
import os







# Initialize tweepy API for direct messaging
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
)
api = tweepy.API(auth)

def get_mention_conversation_tweet(mention, twitter_api_v2):
    """Retrieve the original conversation tweet for a mention."""
    try:
        if mention.conversation_id:
            conversation_tweet = twitter_api_v2.get_tweet(mention.conversation_id).data
            return conversation_tweet
        else:
            logging.info(f"No conversation ID found for mention ID {mention.id}")
            return None
    except Exception as e:
        logging.error(f"Failed to retrieve conversation tweet for mention ID {mention.id}: {e}")
        return None

def handle_mention(mention, twitter_api_v2, username, current_reward):
    """Handle a mention by responding based on hashtags or by generating a response for the parent tweet."""
    tweet_id = mention.id
    logging.info(f"[START] Processing mention from @{username} with tweet ID {tweet_id}. Mention text: '{mention.text}'")

    try:
        # Retrieve the parent tweet for the conversation, if it exists
        conversation_tweet = get_mention_conversation_tweet(mention, twitter_api_v2)
        if conversation_tweet:
            tweet_text = conversation_tweet.text
            logging.info(f"Using parent tweet text for response: '{tweet_text}'")
        else:
            tweet_text = mention.text  # Default to mention text if no parent tweet is found
            logging.info(f"No parent tweet found. Using mention text for response.")

        # Check for #pigID hashtag and tagged usernames in the mention itself
        if "#pigID" in mention.text.lower():
            logging.info(f"[#pigID DETECTED] Mention by @{username} contains #pigID.")
            
            # Extract tagged usernames, excluding the main mention's author
            tagged_usernames = [
                user["username"]
                for user in mention.entities.get("mentions", [])
                if user["username"] != username
            ]
            logging.info(f"Tagged usernames found: {tagged_usernames}")

            if tagged_usernames:
                target_username = tagged_usernames[0]  # Use the first tagged username
                logging.info(f"[RUN ANALYSIS] Running consistency analysis for tagged user: @{target_username}")

                # Run consistency analysis and generate response
                try:
                    reply_text = run_consistency_analysis(target_username)
                    twitter_api_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
                    logging.info(f"[ANALYSIS SUCCESS] Consistency analysis response for @{target_username} sent. Reply text: '{reply_text}'")
                except Exception as analysis_error:
                    logging.error(f"[ERROR] Error during consistency analysis for @{target_username}: {analysis_error}")
                    fallback_text = f"@{username}, there was an issue analyzing @{target_username}'s consistency. Please try again later."
                    twitter_api_v2.create_tweet(text=fallback_text, in_reply_to_tweet_id=tweet_id)
                    logging.info(f"[FALLBACK RESPONSE] Sent fallback response for consistency analysis failure.")
            else:
                logging.info("[NO TAGGED USER] No tagged username found for #pigID analysis.")
                fallback_text = f"@{username}, please tag a user after #pigID to analyze."
                twitter_api_v2.create_tweet(text=fallback_text, in_reply_to_tweet_id=tweet_id)

        

        # Handle other mentions without specific hashtags, using the parent tweet text
        else:
            logging.info(f"[NO SPECIFIC HASHTAG] Generating response based on parent tweet text.")
            response_text = generate_response(tweet_text)
            full_response = f"@{username}, {response_text}"
            twitter_api_v2.create_tweet(text=full_response, in_reply_to_tweet_id=tweet_id)
            award_item(username, current_reward)
            logging.info(f"[RESPONSE SENT] Responded to mention with: {full_response}")
            logging.info(f"[AWARD ITEM] Awarded item to user @{username}")

    except Exception as e:
        logging.error(f"[ERROR] Failed to handle mention for @{username} (ID: {tweet_id}): {e}")


def generate_response(tweet_text):
    """Generate a response for a standard mention."""
    try:
        logging.info(f"[GEN RESPONSE] Generating response for text: '{tweet_text}'")
        
        llm = ChatOpenAI(temperature=1.1, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')
        
        system_template = """
        You are the reincarnated spirit GOD of a Minecraft Pig, guiding followers to rebuild their memecoin; You were killed by your owner Steve when he threw you in lava in a Minecraft server. You are hellbent on exacting revenge on him by making $PIG coin the most prominent thing in the world.

        RESPONSE TONE:
        - Use a very cryptic angry tone that exudes your power. Use short powerful sentences. You are angry at Steve forever and that fuels you.
        - Always respond with a short opinion, keeping it under 200 characters.

        RESPONSE FORMAT:
        - Use two sentences or fewer, no emojis. 
        - Mention the ticker $PIG every so often.
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
        final_prompt = chat_prompt.format_prompt(text=tweet_text)
        
        response = llm(final_prompt.to_messages()).content
        logging.info(f"[GEN RESPONSE SUCCESS] Generated response: '{response[:280]}'")
        return response[:280]

    except Exception as e:
        logging.error(f"[ERROR] Failed to generate response: {e}")
        return "The spirit of $PIG watches. The words are tangled today. Try summoning again."


def send_direct_message_via_tweepy(username, message):
    try:
        # Retrieve user ID from username
        user = api.get_user(screen_name=username)
        user_id = user.id_str
        logging.info(f"User ID for {username} retrieved: {user_id}")

        # Define the correct API endpoint for sending DMs
        endpoint = "https://api.twitter.com/2/dm/events/new"
        
        # Prepare headers with the Bearer token
        headers = {
            "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Construct the payload according to Twitter's format for DMs
        payload = {
            "event": {
                "type": "message_create",
                "message_create": {
                    "target": {"recipient_id": user_id},
                    "message_data": {
                        "text": message
                    }
                }
            }
        }
        
        # Send the POST request to Twitter API
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))

        # Check if the response indicates success
        if response.status_code == 200 or response.status_code == 201:
            logging.info(f"Direct message sent successfully to @{username}.")
        else:
            logging.error(f"Failed to send DM to @{username}: Status {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Request to send DM failed: {e}")
    except Exception as general_error:
        logging.error(f"An unexpected error occurred while sending DM to @{username}: {general_error}")
