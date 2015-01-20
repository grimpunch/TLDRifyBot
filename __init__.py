import ConfigParser
import praw
import re
import time
import pyteaser
import traceback

# Get the account password from the config stored with the bot
config = ConfigParser.ConfigParser()
config.read('account.cfg')


# Create the Reddit instance for all requests
reddit = praw.Reddit(user_agent='TLDRify , the summarizer-bot by /u/grimpunch v1.0'
                                'URL: http://tldrbot.christiancod.es')


# Parse account details from config and login
username = config.get('AccountDetails', 'user', raw=True)
password = config.get('AccountDetails', 'pass', raw=True)
reddit.login(username, password)

alreadyDone = set()


def tldr_already(text):
    if re.findall('((i)T[^\w]*L[^\w]*D[^\w]*R)', text).__len__() > 0:
        return True
    else:
        return False


def create_summaries(title, text):
    summaries = pyteaser.Summarize(title, text)
    formatted_summary = title + u':\n'
    for summary in summaries:
        formatted_summary += u'- ' + summary + u'\n'
    return formatted_summary


def create_summaries_from_url(title, url):
    try:
        summaries = pyteaser.SummarizeUrl(url)
    except:
        return 'No Summary'
    formatted_summary = title + u':\n'
    for summary in summaries:
        formatted_summary += u'- ' + summary + u'\n'
    return formatted_summary


print 'TLDRify online - Logged in and running'


def main():
    subreddit = reddit.get_subreddit('testingground4bots')
    for submission in subreddit.get_hot(limit=20):
        try:
            print 'Post Title', submission.title
            print 'Post url', submission.url
        except:
            pass
        if submission.id not in alreadyDone.__iter__():
            if 'reddit.com' not in submission.url:
                op_url = submission.url
                print 'Post Title', submission.title
                print 'Post ID', submission.id
                alreadyDone.add(submission.id)
                summary = create_summaries_from_url(submission.title, op_url)
                if summary.__len__() > 1200:
                    print 'Summary Length:' , summary.__len__()
                    print 'Rejected for length exceeded'
                msg = '##TLDR: \n' + summary
                submission.add_comment(msg)
                print 'Posted a TLDR successfully'
            else:
                op_text = submission.selftext
                if not (tldr_already(op_text)) and op_text.__len__() > 1000:
                    print 'Post Length:', op_text.__len__()
                    print 'Post Title', submission.title
                    print 'Post ID', submission.id
                    alreadyDone.add(submission.id)
                    summary = create_summaries(submission.title, op_text)
                    if summary.__len__() > 750 and 'No Summary' not in summary:
                        print 'Summary Length:' , summary.__len__()
                        print 'Rejected for length exceeded'
                    msg = '##TLDR: \n' + summary
                    submission.add_comment(msg)
                    print 'Posted a TLDR successfully'
        alreadyDone.add(submission.id)

sleepytime = 5

while True:
    try:
        main()
        if (sleepytime>(7*60)):
            sleepytime = round(sleepytime/2)
            print 'Sleeping for %d seconds between runs'
    except Exception as e:
        #if not successful, slow down.
        if (str(e)=="HTTP Error 504: Gateway Time-out" or str(e)=="timed out"):
            sleepytime = round(sleepytime*2)
            print 'Sleeping for %d seconds between runs'
        else:
            print 'Exception:', e
            traceback.print_exc()
            pass
    time.sleep(sleepytime)
