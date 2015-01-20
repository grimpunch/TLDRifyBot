__author__ = 'Christian Murphy'
import ConfigParser
import praw
import time
import pyteaser

#Get the account password from the config stored with the bot
config = ConfigParser.ConfigParser()
config.read('account.cfg')

reddit = praw.Reddit(user_agent='TLDRify , the summarizer-bot by /u/grimpunch v1.0'
                                'URL: http://tldrbot.christiancod.es')

username, password = config.get('AccountDetails', 'user'), config.get('AccountDetails', 'pass')
