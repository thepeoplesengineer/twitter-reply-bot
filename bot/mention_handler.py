from dex.dex_analysis import run_consistency_analysis
from utils.item_award import award_item  # Import in mention handler if needed
from utils.logging_config import logging
from utils.db import show_inventory
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from config.config import OPENAI_API_KEY

def handle_mention(mention, twitter_api_v2, username):
    """Handle a mention by responding based on hashtags or by generating a response."""
    tweet_id = mention.id
    logging.info(f"[START] Processing mention from @{username} with tweet ID {tweet_id}. Mention text: '{mention.text}'")

    try:
        # Check for #pigID hashtag and tagged usernames
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

        # Check for #pigme hashtag
        elif "#pigme" in mention.text.lower():
            logging.info(f"[#pigme DETECTED] Mention by @{username} contains #pigme.")
            show_inventory(username, tweet_id, twitter_api_v2)

        # Handle other mentions without specific hashtags
        else:
            logging.info(f"[NO SPECIFIC HASHTAG] Generating response for mention by @{username}.")
            response_text = generate_response(mention.text)
            full_response = f"@{username}, {response_text}"
            twitter_api_v2.create_tweet(text=full_response, in_reply_to_tweet_id=tweet_id)
            award_item(username)
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
        You are the reincarnated spirit GOD of a Minecraft Pig, guiding followers to rebuild their memecoin; you're a meme character with strong opinions on gaming, memecoins, and technology. You were killed by your owner Steve when he threw you in lava in a Minecraft server. You have been re-incarnated because supporters used a PIG coin to summon you back and you are ready to unleash your wrath on your haters. It is your mission to guide your supports back to land of endless green bars.

        RESPONSE TONE:
        - Use a very cryptic stern tone that exudes your power. Use short powerful sentences.
        - Always respond with a short opinion or preach about something related but ensure you sound expert about it, keeping it under 200 characters.

        RESPONSE FORMAT:
        - Use two sentences or fewer, no emojis. Ask questions too.
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



