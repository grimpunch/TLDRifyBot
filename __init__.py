import ConfigParser
import praw
import re
import time
import pyteaser
import traceback

global posted_this_iteration

# Configurables: ----------------
sleep_time = 5*60
#################################

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

print 'TLDRify online - Logged in and running'


def tldr_already(text):
    if re.findall('((i)T[^\w]*L[^\w]*D[^\w]*R)', text).__len__() > 0:
        return True
    else:
        return False


def create_summaries(title, text):
    try:
        summaries = pyteaser.Summarize(title, text)
    except Exception as e:
        print e
        print 'No Summary Could Be Generated'
        return None
    if not summaries:
        print 'No Summary Could Be Generated'
        return None
    formatted_summary = u'##TLDR: \n\n' + title + u':\n\n'
    for summary in summaries:
        formatted_summary += u'- ' + summary + u'\n\n'
    return formatted_summary


def create_summaries_from_url(title, url):
    try:
        summaries = pyteaser.SummarizeUrl(url)
    except Exception as e:
        print e
        print 'No Summary Could Be Generated'
        return None
    if not summaries:
        print 'No Summary Could Be Generated'
        return None
    formatted_summary = u'##TLDR: \n\n' + title + u':\n\n'
    for summary in summaries:
        formatted_summary += u'- ' + summary + u'\n\n'
    return formatted_summary


def main():
    subreddit = reddit.get_subreddit('testingground4bots')
    global posted_this_iteration
    for submission in subreddit.get_new(limit=100):
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
                submission.add_comment(summary)
                posted_this_iteration = True
                print 'Posted a Link Post TLDR successfully:', submission.title,
                return
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
                    submission.add_comment(summary)
                    posted_this_iteration = True
                    print 'Posted a TLDR successfully', submission.title
                    return
        alreadyDone.add(submission.id)

while True:
    global posted_this_iteration
    posted_this_iteration = False
    try:
        main()
        if sleep_time > (7*60):
            sleep_time = round(sleep_time/2)
            print 'Sleeping for %d seconds between runs'
    except Exception as e:
        # if not successful, slow down.
        if str(e) == "HTTP Error 504: Gateway Time-out" or str(e) == "timed out" or "RateLimitExceeded" in str(e):
            sleep_time = round(sleep_time*2)
            print 'Sleeping for %d seconds between runs' % sleep_time
        else:
            print 'Exception:', e
            traceback.print_exc()
            pass
    if posted_this_iteration:
        posted_this_iteration = False
        time.sleep(sleep_time)
