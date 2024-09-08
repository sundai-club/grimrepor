import asyncio
import sys
from twikit import Client

# Your Twitter account credentials
USERNAME = 'GrimRepor'
EMAIL = 'nlal@media.mit.edu'
PASSWORD = 'Don\'tfearthepipper!'

# User-Agent string from your browser
USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1)'

# Get the owner_name and repo_name from the command-line arguments
owner_name = sys.argv[1]
repo_name = sys.argv[2]

# The following are test parameters
#owner_name = "nikhilbrijlal"
#repo_name = "ilovepython2.7"


# Create the tweet text
TWEET_TEXT = f"Hey, @{owner_name}, your repository: https://github.com/{owner_name}/{repo_name} can no longer be built! We would love to have you join us over at pip-ai where we can straighten this out for you. <3 Grim-reapor"

# Initialize the Twikit Client with the custom User-Agent
client = Client(user_agent=USER_AGENT)

async def main():
    # Log in to Twitter
    await client.login(
        auth_info_1=USERNAME,
        auth_info_2=EMAIL,
        password=PASSWORD
    )

    # Wait for 10 seconds before posting the tweet
    print("Waiting for 10 seconds before posting the tweet...")
    await asyncio.sleep(10)

     # Try to post a tweet with error handling
    try:
        await client.create_tweet(text=TWEET_TEXT)
        print("Tweet posted successfully!")
    except Exception as e:
        print(f"Sadface homies. Error: {e}")



# Run the script
asyncio.run(main())
