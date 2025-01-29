import os
import praw
import pymongo
import time
from dotenv import load_dotenv
import requests  # <-- New import

load_dotenv()  # Load variables from .env into os.environ

# -----------------------------------
# 1. Configure your Reddit credentials
# -----------------------------------
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")
MONGODB_URI = os.environ.get("MONGODB_URI")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


# Slack incoming webhook URL (you can store it in .env as well)

# -----------------------------------
# 2. Create a PRAW Reddit instance
# -----------------------------------
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Ensure we’re read-only if not authenticated with username/password
reddit.read_only = True

# -----------------------------------
# 3. Set up MongoDB connection
# -----------------------------------

mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client["mnmt_reddit_db"]        # Database name
collection = db["processed_submissions"]   # Collection name

# -----------------------------------
# 4. Define your target subreddits
# -----------------------------------
target_subreddits = ["techno", "festivals", "musicfestivals"]

# -----------------------------------
# 5. Define keywords to look for
# -----------------------------------
keywords = ["mnmt", "monument"]

# -----------------------------------
# 6. Main logic to fetch new submissions and check keywords
# -----------------------------------
def check_submissions():
    """
    Fetch recent submissions from target subreddits, 
    checks for matching keywords, 
    prints thread info if matched and not yet processed, 
    stores them in MongoDB, 
    and sends Slack notification for each match.
    """
    print(f"Checking subreddits: {target_subreddits} for keywords {keywords}...")

    for subreddit_name in target_subreddits:
        subreddit = reddit.subreddit(subreddit_name)
        
        for submission in subreddit.new(limit=50):
            submission_id = submission.id

            # Check if we already processed this submission
            if collection.find_one({"_id": submission_id}):
                continue

            # Prepare text to search
            title_text = submission.title.lower() if submission.title else ""
            selftext_text = submission.selftext.lower() if submission.selftext else ""

            # Check for keywords
            if any(keyword in title_text or keyword in selftext_text for keyword in keywords):
                # Print to terminal
                print("\n--- MATCH FOUND ---")
                print(f"Subreddit: r/{subreddit_name}")
                print(f"Title: {submission.title}")
                print(f"URL: {submission.url}")
                print(f"Reddit Link: https://reddit.com{submission.permalink}")
                print(f"Author: {submission.author}")
                print("-------------------\n")

                # 1. Store in MongoDB
                collection.insert_one({
                    "_id": submission_id,
                    "title": submission.title,
                    "url": submission.url,
                    "permalink": submission.permalink,
                    "subreddit": subreddit_name,
                    "author": str(submission.author),
                    "created_utc": submission.created_utc
                })

                # 2. Send Slack message
                if SLACK_WEBHOOK_URL:
                    slack_message = (
                        f"*MATCH FOUND!*\n"
                        f"*Subreddit:* r/{subreddit_name}\n"
                        f"*Title:* {submission.title}\n"
                        f"*URL:* {submission.url}\n"
                        f"<https://reddit.com{submission.permalink}|Reddit Link>\n"
                    )
                    try:
                        response = requests.post(
                            SLACK_WEBHOOK_URL,
                            json={"text": slack_message},
                            timeout=10
                        )
                        # Optional: check Slack response
                        if response.status_code != 200:
                            print(f"Slack webhook failed: {response.text}")
                    except Exception as e:
                        print(f"Error sending Slack notification: {e}")

# -----------------------------------
# 7. Run once or schedule
# -----------------------------------
if __name__ == "__main__":
    # Option A: Run it once
    check_submissions()

    # Option B: Run in a loop with sleep
    # while True:
    #     check_submissions()
    #     time.sleep(43200)
