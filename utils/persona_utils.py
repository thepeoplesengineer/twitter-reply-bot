import sqlite3

def get_tweet_corpus():
    """Combine all tweet texts into a single corpus for persona building."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT tweet_text FROM tweets")
    tweets = [row[0] for row in cursor.fetchall()]
    conn.close()
    return " ".join(tweets)
