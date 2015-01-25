import logging
import ConfigParser
from random import random
from bisect import bisect
import praw
import re
import time
import pyteaser
import traceback
import sys

global posted_this_iteration

# System Configuration: ----------------
sleep_time = 5*60
subreddit_to_scan = 'all'
bot_author_message = """---------------\n\nHi I'm a bot! I was made by /u/grimpunch, if I've gone awry, message him and he'll come fix me. \n\n If you don't want me in your sub, it's okay to ban me I won't mind"""
#################################

# Prepare logging
logging.basicConfig(level=logging.INFO, filename="logfile", filemode="a+",
                    format="%(asctime) -15s %(levelname) -8s %(message)s")
root = logging.getLogger()
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)
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

posts_already_done = set()
comments_already_done = set()

logging.info('TLDRify online - Logged in and running')


def get_subreddit():
    return reddit.get_subreddit(subreddit_to_scan)


def weighted_choice(choices):
    values, weights = zip(*choices)
    total = 0
    cum_weights = []
    for w in weights:
        total += w
        cum_weights.append(total)
    x = random() * total
    i = bisect(cum_weights, x)
    return values[i]


def tldr_already(text):
    if re.findall('((i)T[^\w]*L[^\w]*D[^\w]*R)', text).__len__() > 0:
        return True
    else:
        return False


def handle_link_post_summary(submission=None, comment=None):
    global posted_this_iteration
    op_url = submission.url
    logging.info(msg=('Post Title', submission.title))
    logging.info(msg=('Post ID', submission.id))
    posts_already_done.add(submission.id)
    summary = create_summaries(title=submission.title, url=op_url)
    if summary.__len__() > 1200:
        logging.info(msg=('Summary Length:', summary.__len__()))
        logging.info(msg=('Rejected for length exceeded'))
    if comment:
        comment.reply(summary)
    else:
        submission.add_comment(summary)
    posted_this_iteration = True
    logging.info(msg=('Posted a Link Post TLDR successfully:', submission.title))
    if comment:
        logging.info(msg=('requested by:', comment.author))


def handle_self_post_reply(submission, comment, op_text):
    global posted_this_iteration
    logging.info(msg=('Post Length:', op_text.__len__()))
    logging.info(msg=('Post Title', submission.title))
    if comment:
        logging.info(msg=('Post ID', comment.submission.id))
    else:
        logging.info(msg=('Post ID', submission.id))
    posts_already_done.add(submission.id)
    if comment:
        summary = create_summaries(title=comment.submission.title, text=op_text)
    else:
        summary = create_summaries(title=submission.title, text=op_text)
    if summary.__len__() > 750 and 'No Summary' not in summary:
        logging.info(msg=('Summary Length:', summary.__len__()))
        logging.info(msg=('Rejected for length exceeded'))
    if comment:
        comment.reply(summary)
    else:
        submission.add_comment(summary)
    posted_this_iteration = True
    logging.info(msg=('Posted a Self Text TLDR successfully', submission.title))
    if comment:
        logging.info(msg=('by request of', comment.author))


def create_summaries(title=None, text=None, url=None):
    try:
        if url:
            summaries = pyteaser.SummarizeUrl(url)
        else:
            summaries = pyteaser.Summarize(title, text)
    except Exception as e:
        logging.error(msg=(e))
        logging.info(msg=('No Summary Could Be Generated'))
        return None
    if not summaries:
        logging.info(msg=('No Summary Could Be Generated'))
        return None
    formatted_summary = u'##TLDR: \n\n' + title + u':\n\n'
    for summary in summaries:
        formatted_summary += u'- ' + summary.decode('utf-8', errors='ignore') + u'\n\n'
    formatted_summary += u'\n\n' + bot_author_message
    return formatted_summary


def check_for_requests():
    logging.info(msg=('Checking for Requests'))
    subreddit = get_subreddit()
    global posted_this_iteration
    for comment in subreddit.get_comments(limit=100):
        cid = str(comment.id)
        match = re.search('TL;?DR please', comment.body, re.IGNORECASE)
        if match and cid not in comments_already_done:
            comments_already_done.add(cid)
            logging.info(msg=('Found request:', comment.body))
            if comment.is_root:
                logging.info(msg=('Not a child of a comment, process the link or self post'))
                submission = reddit.get_submission(submission=comment.submission)
                if submission.id not in posts_already_done:
                    if 'reddit.com' not in submission.url:
                        handle_link_post_summary(submission=submission, comment=comment)
                        return
                    else:
                        op_text = submission.selftext
                        if not (tldr_already(op_text)) and op_text.__len__() > 1000:
                            handle_self_post_reply(submission, comment, op_text)
                            return
            else:
                logging.info(msg=('Child of comment:', comment.parent_id, '\nFormat into summary of parent'))
                comment_parent = reddit.get_info(thing_id=comment.parent_id).body
                if not (tldr_already(comment_parent)) and comment_parent.__len__() > 1000:
                    handle_self_post_reply(submission=comment.submission, comment=comment, op_text=comment_parent)
                    return
        comments_already_done.add(cid)


def summarize_content_autonomously():
    logging.info(msg=('Looking for content to summarize'))
    subreddit = reddit.get_subreddit(subreddit_to_scan)
    global posted_this_iteration
    for submission in subreddit.get_new(limit=100):
        if submission.id not in posts_already_done:
            if 'reddit.com' not in submission.url:
                handle_link_post_summary(submission=submission)
                return
            else:
                op_text = submission.selftext
                if not (tldr_already(op_text)) and op_text.__len__() > 1000:
                    handle_self_post_reply(submission=submission, op_text=op_text)
                    return
        posts_already_done.add(submission.id)


while True:
    global posted_this_iteration
    posted_this_iteration = False
    try:
        task = weighted_choice([(summarize_content_autonomously, 1), (check_for_requests, 99)])
        task()
        if sleep_time > (7*60):
            sleep_time = round(sleep_time/2)
            logging.info(msg=('Sleeping for %d seconds between runs' % sleep_time))
    except Exception as e:
        # if not successful, slow down.
        if str(e) == "HTTP Error 504: Gateway Time-out" or "timed out" in str(e):
            sleep_time = round(sleep_time*2)
            logging.info(msg=('Sleeping for %d seconds between runs' % sleep_time))
            time.sleep(sleep_time)
        else:
            logging.info(msg=('Exception:', e))
            traceback.print_exc()
            if "RateLimitExceeded" in str(e):
                logging.info(msg=('RATE LIMIT EXCEEDED : ', str(e)))
                sleep_time = round(sleep_time*2)
                time.sleep(sleep_time)
            pass

    if posted_this_iteration:
        posted_this_iteration = False
        logging.info(msg=('Sleeping for %d seconds' % sleep_time))
        time.sleep(sleep_time)
    else:
        logging.info(msg=('Sleeping for %d seconds' % sleep_time))
        time.sleep(10)
