import tweepy

# Your API keys and access tokens from the Twitter Developer Portal
API_KEY = 'EeF8fR5OHF6jdNLL08Jzn9l3s'
API_SECRET_KEY = 'IDw6l1tDfZSgWdDk8hJNPepxtGFXzGbKhGa2jrKnMsEL1CnbD4'
ACCESS_TOKEN = '1832867949637459968-0oPb7Wp3rjVaQqEOqxs9c8OwkU5mEO'
ACCESS_TOKEN_SECRET = '47IsOVbiA2w96pUuhXDRL5J52FGy2ICKrYWdITWrlns1I'

# Authenticate to Twitter
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Create the Tweepy API object
api = tweepy.API(auth)

# Post a tweet
tweet = "Hello, world! This is a tweet from Tweepy."
api.update_status(status=tweet)

print("Tweet posted successfully!")
