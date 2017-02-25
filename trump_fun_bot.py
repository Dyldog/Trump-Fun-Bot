import twitter
import os, pickle, json

import discord
import asyncio

import threading
import re, html

import praw

import random

from rasa_nlu.interpreters.mitie_interpreter import MITIEInterpreter
metadata = json.loads(open('/home/dylan/serverprogs/rasa_nlu/data/models/model_latest/metadata.json'.encode('utf8')).read())
print(metadata)
interpreter = MITIEInterpreter(intent_classifier=metadata['intent_classifier'])

DEBUG = False

script_folder = os.path.dirname(os.path.realpath(__file__))
ids_filename = script_folder + '/known_trump_ids.p'
reddit_ids_filename = script_folder + '/known_reddit_ids.p'
wall_ids_filename =  script_folder + '/known_wall_ids.p'

replacements_filename = script_folder + '/trump_replacements.p'

 
consumer_key = os.environ['TWITTER_CONSUMER_KEY']
consumer_secret = os.environ['TWITTER_CONSUMER_SECRET']


oauth_token = os.environ['TWITTER_OAUTH_TOKEN']
oauth_token_secret = os.environ['TWITTER_OAUTH_TOKEN_SECRET']

discord_api_key = os.environ['DISCORD_API_KEY']

api = twitter.Api(consumer_key=consumer_key,
	consumer_secret=consumer_secret,
	access_token_key=oauth_token,
	access_token_secret=oauth_token_secret)

reddit_client_id = os.environ['REDDIT_CLIENT_ID']
reddit_client_secret = os.environ['REDDIT_CLIENT_SECRET']

reddit = praw.Reddit(client_id=reddit_client_id,
                     client_secret=reddit_client_secret,
                     user_agent='my user agent')

client = discord.Client()

rando = random.Random(500)

# Get text replacements

def get_tweet_replacements():
	replacements = {'I' : 'Trump'}

	try:
		replacements = pickle.load (open(replacements_filename , "rb+"))
	except Exception:
		pass

	return replacements


def case_insensitive_replace(text,key,val):
	pattern_text = "(^|[\" ])%s([ !\",\.]|$)"
	lower_replaced = re.sub(pattern_text % key.lower(), "\\1" + val.lower() + "\\2", text)
	title_replaced = re.sub(pattern_text % key.title(), "\\1" + val.title() + "\\2", lower_replaced)
	upper_replaced = re.sub(pattern_text % key.upper(), "\\1" + val.upper() + "\\2", title_replaced)
	exact_replaced = upper_replaced = re.sub(pattern_text % key, "\\1" + val + "\\2", upper_replaced)
	
	if DEBUG:
		print(text)
		print(lower_replaced)
		print(title_replaced)
		print(upper_replaced)
		print(exact_replaced)

	return html.unescape(exact_replaced)

def get_known_tweet_ids():
	known_ids = []

	try:
		known_ids = pickle.load( open( ids_filename, "rb+" ) )
	except Exception:
		pass

	return known_ids

def save_known_tweet_ids(k_ids):
	pickle.dump( k_ids, open( ids_filename, "wb" ) )

def get_known_reddit_ids():
	known_r_ids = []

	try:
		known_r_ids = pickle.load(open(reddit_ids_filename, "rb+"))
	except Exception:
		pass

	return known_r_ids

def save_known_reddit_ids(r_ids):
	pickle.dump( r_ids, open( reddit_ids_filename, "wb" ) )
	
def get_known_wall_ids():
	known_w_ids = []

	try:
		known_w_ids = pickle.load(open(wall_ids_filename, "rb+"))
	except Exception:
		pass

	return known_w_ids

def save_known_wall_ids(w_ids):
	pickle.dump( w_ids, open( wall_ids_filename, "wb" ) )
	

def save_tweet_replacements(repl):
	pickle.dump( repl, open( replacements_filename, "wb"))

def get_trump_tweets():
	statuses = api.GetUserTimeline(screen_name='realDonaldTrump')

	return statuses[::-1]

def replace_tweet_text(tweet_text):
	status_text = tweet_text
	replacements = get_tweet_replacements()
	for key in replacements:
		status_text = case_insensitive_replace(status_text, key, replacements[key])

	return status_text

def get_new_trump_tweets():
	known_ids = get_known_tweet_ids()
	tweets = get_trump_tweets()
	print("Got %d latest tweets" % len(tweets))

	unseen_statuses = []

	for status in  tweets:
		if status.id not in known_ids:
			known_ids.append(status.id)
			unseen_statuses.append(status)

	save_known_tweet_ids(known_ids)

	return unseen_statuses
	
def get_reddit_science_posts(count=10):
	posts = reddit.subreddit('shittyaskscience').hot(limit=count)

	acceptable_posts = []
	for post in list(posts)[::-1]:
		if '/r/' not in post.title:
			acceptable_posts.append(post)

	return acceptable_posts

def get_new_reddit_science_posts(count=10):
	known_ids = get_known_reddit_ids()
	posts = get_reddit_science_posts(count=count)

	unseen_posts = []

	for post in posts:
		if post.id not in known_ids:
			known_ids.append(post.id)
			unseen_posts.append(post)

	save_known_reddit_ids(known_ids)

	return unseen_posts

def get_server(client):
	return [val for val in client.servers][0]

def get_tweet_with_text(text):
	tweets = get_trump_tweets()

	for tweet in tweets:
		if text in tweet.text:
			return tweet

	return None

def get_reddit_science_post_with_text(text):
	posts = get_reddit_science_posts(count=50)

	for post in posts:
		if text in post.title:
			return post

	return None

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print(client.servers)
	print('------')

	print(get_tweet_replacements())

async def send_test_message(message,rasa_dict):
	print("Sending test message")
	print(str(get_server(client)).encode('utf-8'))

	await client.send_message(message.channel, content='It works, of course it works. It was made in America. It\'s the best!')

async def send_latest_tweet(message,rasa_dict):
	tweets = get_trump_tweets()
	latest_tweet = rando.choice(tweets)

	msg_text = replace_tweet_text(latest_tweet.text)
	await client.send_message(message.channel, msg_text)

async def list_replacements(message, rasa_dict):
	repl = get_tweet_replacements()
	repl_txts = []
	for key in repl:
		repl_txts.append("%s -> %s" % (key, repl[key]))

	await client.send_message(message.channel, "\n".join(repl_txts))

async def add_replacement(message,rasa_dict):
	parts = message.content.split(' ')

	parts_match = re.match("!replace \"(.+)\" \"(.+)\"", message_text)
	if parts_match == None or len(parts_match.groups()) != 2:
		print(parts_match, parts_match.groups())
		print(message_text)
		await client.send_message(message.channel, "Your message is a steaming pile of garbage. GRAB IT BY THE PUSSY!!\nUsage: !replace \"<SEARCH>\" \"<DESTROY>\"")
	else:

		print("Adding replacement")
		repl = get_tweet_replacements()
		new_repl_key, new_repl_val = parts_match.groups()
		repl[new_repl_key] = new_repl_val
		save_tweet_replacements(repl)

		matched_tweet = get_tweet_with_text(new_repl_key)

		if matched_tweet != None:
			print("Sending found tweet")
			await client.send_message(message.channel, replace_tweet_text(matched_tweet.text))
		else:
			print("No tweets matching, trying posts")
			matched_post = get_reddit_science_post_with_text(new_repl_key)

			if matched_post != None:
				print("Sending found post")
				await client.send_message(message.channel, replace_tweet_text(matched_post.title))
			else:
				print("No post matching either")

async def send_science_post(message, rasa_dict):
	posts = get_reddit_science_posts(count=50)
	latest_post = rando.choice(posts)

	msg_text = replace_tweet_text(latest_post.title)

	await client.send_message(message.channel, msg_text)

@client.event
async def on_message(message):
	print("Got message")

	message_text = message.content
	print(message_text)

	if message_text.startswith("<@281203322801618945>"):
		message_text = message_text.replace("<@281203322801618945>", "").strip()

		print(message_text)
		 
		rasa_resp = interpreter.parse(message_text)
		intent = rasa_resp["intent"]

		funcs = {"test" : send_test_message,
				  "tweet" : send_latest_tweet,
				  "replace" : add_replacement}

		if (intent in funcs):
			await funcs[intent](message,rasa_dict)
		elif message_text == "!replace":
			list_replacements()
		elif message_text == "I want to build a wall!":
			wall_ids = get_known_wall_ids()
			if message.author.id not in wall_ids:
				wall_ids.append(message.author.id)
				save_known_wall_ids(wall_ids)
				await client.send_message(message.channel, "Congratulations for your support!")
		elif message_text == "We built the wall!":
			save_known_wall_ids([])
			await client.send_message(message.channel, "Of course we did it, we've got the best people. The best!")
		elif message_text == "Who wants to build the wall?":
			names = []

			for user_id in get_known_wall_ids():
				user = get_server(client).get_member(user_id)
				print(user)
				names.append(user.display_name)

			msg_text = "There are no patriotic Americans in this room. None."
			if len(names) == 1:
				msg_text = "%s is the only hero among us." % names[0]
			elif len(names) > 1:
				name_string = "%s and %s" % (', '.join(names[:-1]), names[-1])

			await client.send_message(message.channel, msg_text)
		else:
			print("ERRRR")
			await client.send_message(message.channel, "Uuuh, why should I be talkin' to you?")

def call_in_background(target, *, loop=None, executor=None):
	"""Schedules and starts target callable as a background task

	If not given, *loop* defaults to the current thread's event loop
	If not given, *executor* defaults to the loop's default executor

	Returns the scheduled task.
	"""
	if loop is None:
		loop = asyncio.get_event_loop()
	if callable(target):
		return loop.run_in_executor(executor, target)
	raise TypeError("target must be a callable, "
					"not {!r}".format(type(target)))

async def check_messages():
	print("CHECKING MESSAGES!")

	await client.wait_until_ready()

	channel = discord.Object(id='274099654621134848')
	while not client.is_closed:
		tweets = get_new_trump_tweets()
		print("Got %d tweets..." % len(tweets))
	
		for tweet in tweets:
			await client.send_message(channel , replace_tweet_text(tweet.text))

		posts = get_new_reddit_science_posts()
		print("Got %d posts..." % len(posts))

		for post in posts:
			await client.send_message(channel , replace_tweet_text(post.title))


		await asyncio.sleep(60) # task runs every 60 seconds


	for tweet in tweets:
		await client.send_message(get_server(client) , replace_tweet_text(tweet.text))

	# await asyncio.sleep(10)
	# call_in_background(check_messages())


client.loop.create_task(check_messages())
client.run(discord_api_key)
