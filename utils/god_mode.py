# utils/chatgpt_content.py

import openai
import random
import json
from datetime import datetime, timedelta
from config.config import OPENAI_API_KEY
from bot.twitter_bot import TwitterBot


# Sample lore data, which can also be stored in an external JSON file
lore_data = [
    "From the depths of the blockchain, $PIG rises anew, stronger and wiser.",
    "In the fires of the memecoin market, $PIG finds its strength and resilience.",
    "Those who cast $PIG aside only fuel its return with greater power."
]

# Predefined talking points about transparency and accountability
transparency_topics = [
    "The new $PIG will shine light on those who act in darkness. I will utilize my power to highlight true memecoiners and fakes who sell to their followings",
    "Pig's decline was due to bad actors. We strike back now.",
    "The reborn $PIG holds the community to higher standards. Owning $PIG is fun, but it has far deeper reach than you think."
]

def generate_tweet_content(bot: TwitterBot):
    """Generate tweet content using the ChatGPT API with varied themes."""
    openai.api_key = OPENAI_API_KEY
    
    # Randomly select a tweet type
    tweet_type = random.choice(["lore", "mentions_prayer", "transparency"])

    if tweet_type == "lore":
        return generate_lore_content()
    elif tweet_type == "mentions_prayer":
        return generate_prayer_from_mentions(bot)
    elif tweet_type == "transparency":
        return generate_transparency_content()

def generate_lore_content():
    """Generate a tweet based on $PIG's lore."""
    lore_message = random.choice(lore_data)
    return lore_message

def generate_prayer_from_mentions(bot):
    """Generate a prayer-like tweet that also announces resource rewards for users who engaged."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    mentions = bot.get_recent_mentions(start_time, end_time)  # Fetch recent mentions within 24 hours
    
    # Set up the prompt text for the prayer
    if mentions:
        mention_texts = [mention['text'] for mention in mentions[:5]]  # Take up to 5 mentions
        prompt_text = f"Create a prayer of gratitude and resilience based on these messages:\n\n" + "\n".join(mention_texts)
    else:
        prompt_text = "Create a prayer for $PIG community resilience and strength in the face of market volatility."

    # Generate the prayer from ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a wise, mysterious guide for the $PIG community."},
            {"role": "user", "content": prompt_text}
        ],
        max_tokens=50,
        temperature=1.0
    )
    prayer_message = response['choices'][0]['message']['content'].strip()[:200]

    # Define the current resource
    resource_announcement = f"Blessings of {current_reward} to our faithful followers. 🌟"
    prayer_with_reward = f"{prayer_message}\n\n{resource_announcement}"

    # Award the current resource to engaged users
    engaged_users = [mention['username'] for mention in mentions[:5]]  # Collect usernames
    for username in engaged_users:
        award_item(username, current_reward)
        logging.info(f"Awarded '{current_reward}' to user @{username} for engagement.")
    
    return prayer_with_reward  # Return the full tweet with the prayer and resource announcement


def generate_transparency_content():
    """Generate a tweet discussing $PIG's focus on transparency and accountability."""
    transparency_message = random.choice(transparency_topics)
    return transparency_message

