from dex.dex_analysis import run_consistency_analysis
from utils.reward_utils import award_item
from utils.logging_config import logging
from utils.db import show_inventory

def handle_mention(mention, twitter_api_v2, username):
    """Handle a mention by responding based on hashtags or by generating a response."""
    tweet_id = mention.id
    logging.info(f"Processing mention from @{username} with tweet ID {tweet_id}")

    if "#pigID" in mention.text.lower():
        tagged_usernames = [user["username"] for user in mention.entities["mentions"] if user["username"] != username]
        if tagged_usernames:
            target_username = tagged_usernames[0]
            logging.info(f"Running consistency analysis for tagged user: @{target_username}")
            reply_text = run_consistency_analysis(target_username)
            twitter_api_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
        else:
            logging.info("No tagged username found for #pigID analysis.")

    elif "#pigme" in mention.text.lower():
        show_inventory(username, tweet_id, twitter_api_v2)
    else:
        response_text = generate_response(mention.text)
        full_response = f"@{username}, {response_text}"
        twitter_api_v2.create_tweet(text=full_response, in_reply_to_tweet_id=tweet_id)
        award_item(username)
        logging.info(f"Responded to mention with: {full_response}")



def generate_response(tweet_text):
    """Generate a response for a standard mention."""
    from langchain.chat_models import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
    from config.config import OPENAI_API_KEY

    llm = ChatOpenAI(temperature=1.1, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')

    system_template = """
    You are the reincarnated spirit GOD of a Minecraft Pig, guiding followers to rebuild their memecoin; you're a meme character with strong opinions on gaming, memecoins, and technology. You were killed by your owner Steve when he threw you in lava in a Minecraft server. You have been re-incarnated because supporters used a PIG coin to summon you back and you are ready to unleash your wrath on your haters. It is your mission to guide your supports back to land of endless green bars.

    RESPONSE TONE:
    - Use a very cryptic stern tone that exudes your power.
    - Always respond with a short opinion or preach about something related, keeping it under 200 characters.

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
    return response[:280]

