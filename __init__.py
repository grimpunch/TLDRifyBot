#!/usr/bin/python2
import logging
import ConfigParser
from random import random
from bisect import bisect
import praw
import re
import time
import pyteaser
from goose import Goose
import sys

global posted_this_iteration

# System Configuration: ----------------
sleep_time_setting = 5*60
subreddit_to_scan = 'all'
bot_author_message = """---------------\n\nHi I'm a bot! I was made by /u/grimpunch, if I've gone awry, message him and he'll come fix me. \n\n If you don't want me in your sub, it's okay to ban me I won't mind \n\n I can be summoned in a comment if you say 'TLDR please'"""
percentage_of_op_length_limit = 35.0 # How much of the original article length , in percentage of the original article, must a summary be below.
negative_feedback_threshold = -1 # Score a TLDR must be on Reddit before we go back and delete it because it's unloved </3
subreddit_from_submission = None # Defined in global scope so we can reference the value from exceptions

# Logging configuration
logging.basicConfig(level=logging.INFO, filename="logfile", filemode="a+",
                    format="%(asctime) -15s %(levelname) -8s %(message)s")
root = logging.getLogger()
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)
logging.addLevelName( logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
logging.addLevelName( logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))

# Get the account password from the config stored with the bot
config = ConfigParser.ConfigParser()
try:
    config.read('account.cfg')
except:
    logging.exception('Config File problem, does account.cfg exist?')

# Create the Reddit instance for all requests
reddit = praw.Reddit(user_agent='TLDRify , the summarizer-bot by /u/grimpunch v1.0'
                                'URL: http://tldrbot.christiancod.es')

# Parse account details from config and login
username = config.get('AccountDetails', 'user', raw=True)
password = config.get('AccountDetails', 'pass', raw=True)
reddit.login(username, password)

posts_already_done = set()
comments_already_done = set()

#################################
bad_subreddits = []

with open('badsubreddits') as bs:
    for l in bs.readlines():
        bad_subreddits.append(l.strip())
    bs.close()
logging.info('Ignoring requests and not autonomously processing posts from %s' % str(bad_subreddits).strip('[]'))
#################################

logging.info("TLDRify online - Logged in and running")


def get_subreddit():
    return reddit.get_subreddit(subreddit_to_scan)

def cleanup_memory_usage():
    logging.info('Sets for posts or comments processed getting large, cleaning up')
    posts_already_done.clear()
    comments_already_done.clear()

def sleep(time_to_sleep=sleep_time_setting):
    """Wraps sleeping with a default sleep amount we usually use, and the functionality to log it"""
    logging.info(msg=('Sleeping for %d seconds between runs' % time_to_sleep))
    time.sleep(time_to_sleep)

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
    if re.findall('((?i)T[^\w]*L[^\w]*D[^\w]*R)', text).__len__() > 0:
        return True
    else:
        return False


def filter_bad_urls(url):
    # Avoiding particular content types that are either hard to summarise or just not welcome to be auto-replied to
    bad_urls = ['youtu', 'imgur', 'vid.us', 'vimeo']
    for bad_url in bad_urls:
        if bad_url in url:
            return False
    return True

def filter_bad_subreddits(subreddit):
    # Avoiding particular subs where we think we might not be welcome.
    for sub in bad_subreddits:
        if sub in subreddit:
            return False
    return True

def add_bad_subreddit(badsub=None):
    if badsub not in bad_subreddits:
        with open('badsubreddits', 'a') as bs:
            bs.write('\n'+badsub)
            bs.close()
        logging.info('Adding %s to list of bad_subreddits not to work in, due to banning or massive unpopularity' % badsub)
        bad_subreddits.append(badsub)
    return


def handle_link_post_summary(submission=None, comment=None, subreddit_origin=None):
    global posted_this_iteration
    op_url = submission.url
    logging.info(msg=('Post Title', submission.title))
    logging.info(msg=('Post ID', submission.id))
    posts_already_done.add(submission.id)
    summary = create_summaries(title=submission.title, url=op_url, subreddit_origin=submission.subreddit)
    if not summary:
        return
    original_content_length = len(str(Goose().extract(url=op_url).cleaned_text.encode('utf-8', 'ignore')))
    # Gets the article the same way pyteaser does and checks the length, casting it to a float for testing percentage.

    percentage_of_op_length = 100 * len(summary) / float(original_content_length)

    logging.info('content length: %s' % original_content_length)
    logging.info('summary length: %s' % summary.__len__())
    logging.info('percentage: %s' % percentage_of_op_length)

    if percentage_of_op_length > percentage_of_op_length_limit:
        logging.info(msg=('Summary Length:', summary.__len__()))
        logging.info(msg='Rejected for length exceeded')
        return
    if comment:
        comment.reply(summary)
    else:
        submission.add_comment(summary)
    posted_this_iteration = True
    logging.info(msg=('Posted a Link Post TLDR successfully:', submission.title))
    if comment:
        logging.info(msg=('requested by:', comment.author))


def handle_self_post_reply(submission=None, comment=None, op_text=None, subreddit_origin=None):
    global posted_this_iteration
    logging.info(msg=('Post Length:', op_text.__len__()))
    logging.info(msg=('Post Title', submission.title))
    if comment:
        logging.info(msg=('Post ID', comment.submission.id))
    else:
        logging.info(msg=('Post ID', submission.id))
    posts_already_done.add(submission.id)
    if comment:
        summary = create_summaries(title=comment.submission.title, text=op_text, subreddit_origin=subreddit_origin)
    else:
        summary = create_summaries(title=submission.title, text=op_text, subreddit_origin=subreddit_origin)
    if not summary:
        logging.warning(msg='A summary could not be generated')
        return
    original_content_length = len(op_text)
    percentage_of_op_length = 100 * len(summary) / float(original_content_length)

    logging.info('content length: %s' % original_content_length)
    logging.info('summary length: %s' % summary.__len__())
    logging.info('percentage: %s' % percentage_of_op_length)

    if percentage_of_op_length > percentage_of_op_length_limit:
        logging.info(msg=('Summary Length:', summary.__len__()))
        logging.warning(msg='Rejected for length exceeded')
        return
    if comment:
        comment.reply(summary)
    else:
        submission.add_comment(summary)
    posted_this_iteration = True
    logging.info(msg=('Posted a Self Text TLDR successfully', submission.title))
    if comment:
        logging.info(msg=('by request of', comment.author))


def create_summaries(title=None, text=None, url=None, subreddit_origin=None):
    try:
        if url:
            summaries = pyteaser.SummarizeUrl(url)
        else:
            summaries = pyteaser.Summarize(title, text)
    except Exception as summary_exception:
        logging.exception(msg=summary_exception.message)
        logging.info(msg='No Summary Could Be Generated')
        return
    if not summaries:
        logging.info(msg='No Summary Could Be Generated')
        return
    TLDR_header = u'##TLDR: \n\n'
    if str(subreddit_origin) == "legaladvice":
        TLDR_header = '##OBJECTION!\n\n#TLDR:\n\n'
        logging.info('Making special summary for my buddies at /r/legaladvice')
    formatted_summary = TLDR_header + title + u':\n\n'
    for summary in summaries:
        formatted_summary += u'- ' + summary.decode('utf-8', errors='ignore') + u'\n\n'
    formatted_summary += u'\n\n' + bot_author_message
    if str(subreddit_origin) == "legaladvice":
        formatted_summary += u'\n\n Thanks for using my bot /r/legaladvice!'
    return formatted_summary


def handle_post_from_comment_request(comment=None):
    submission = reddit.get_submission(url=comment.permalink)
    logging.info(msg='Not a child of a comment, process the link or self post')
    if submission.id not in posts_already_done:
        if 'reddit.com' not in submission.url:
            if filter_bad_urls(submission.url):
                handle_link_post_summary(submission=submission, comment=comment, subreddit_origin=submission.subreddit)
                return
            else:
                logging.warning("Filtered possible image/video based link")
            return
        else:
            op_text = submission.selftext
            if not (tldr_already(op_text)) and op_text.__len__() > 1000:
                handle_self_post_reply(submission=submission, comment=comment, subreddit_origin=submission.subreddit, op_text=op_text)
                return


def handle_comment_from_comment_request(comment=None):
    comment_parent = reddit.get_info(thing_id=comment.parent_id).body
    logging.info(msg=('Child of comment:', comment_parent, '\nFormat into summary of parent'))
    if not (tldr_already(comment_parent)) and comment_parent.__len__() > 1000:
        handle_self_post_reply(submission=comment.submission, comment=comment, op_text=comment_parent)
        return


def check_old_posts():
    logging.info(msg='Checking old posts negative feedback')
    user = reddit.get_redditor(username)
    own_posts = user.get_comments()
    bad_posts_found = False
    for post in own_posts:
        if post.score <= negative_feedback_threshold:
            if post.score <= negative_feedback_threshold * 3: # Massively unpopular, cohesively unwanted
                add_bad_subreddit(str(post.subreddit))
            bad_posts_found = True
            logging.info('Removing TLDR of "%s" in "%s", because it had a score of %s' % (post.submission.title, post.subreddit,post.score))
            post.delete()
    if bad_posts_found:
        logging.info("Old posts with negative feedback deleted")
        return
    else:
        logging.info("No negative feedback found, keep on truckin'")
        return


def check_for_requests():
    logging.info(msg='Checking for Requests')
    subreddit = get_subreddit()
    global posted_this_iteration
    for comment in subreddit.get_comments(limit=None):
        cid = str(comment.id)
        match = re.search('TL;?DR please', comment.body, re.IGNORECASE)
        if match and cid not in comments_already_done:
            if username in str(comment.author):
                # Don't reply to the bot itself.
                logging.info('Found comment from %s , so ignore it' % username)
                return
            logging.info(msg=('Found request:', comment.body))
            comments_already_done.add(cid)
            if comment.is_root:
                handle_post_from_comment_request(comment)
                return
            else:
                handle_comment_from_comment_request(comment)



def summarize_content_autonomously():
    logging.info(msg='Looking for content to summarize')
    subreddit = reddit.get_subreddit(subreddit_to_scan)
    global posted_this_iteration
    for submission in subreddit.get_new(limit=100):
        if submission.id not in posts_already_done:
            posts_already_done.add(submission.id)
            if 'reddit.com' not in submission.url:
                if filter_bad_urls(submission.url):
                    subreddit_from_submission = submission.subreddit
                    logging.info('Subreddit this post is from - %s' % str(submission.subreddit))
                    if filter_bad_subreddits(str(submission.subreddit)):
                        handle_link_post_summary(submission=submission)
                        return
                    else:
                        logging.warning('Not going to summarise a post in %s' % subreddit_from_submission)
                        return
                else:
                    logging.warning("Filtered possible image/video based link")
                    return
            else:
                op_text = submission.selftext
                if not (tldr_already(op_text)) and op_text.__len__() > 1000:
                    handle_self_post_reply(submission=submission, op_text=op_text)
                    return


while True:
    global posted_this_iteration
    # noinspection PyRedeclaration
    posted_this_iteration = False

    try:
        task = weighted_choice([(summarize_content_autonomously, 1), (check_old_posts, 50), (check_for_requests, 449)])
        task()
        if sleep_time_setting > (7*60):
            sleep_time_setting = round(sleep_time_setting/2)
            logging.info(msg=('Sleeping for %d seconds between runs' % sleep_time_setting))
        if sleep_time_setting < 3*60:
            sleep_time_setting = round(5*60)
    except Exception as e:
        # if not successful, slow down.
        if str(e) == "HTTP Error 504: Gateway Time-out" or "503" in str(e):
            sleep(round(sleep_time_setting*2))
        elif "MemoryError" in str(e):
            cleanup_memory_usage()
            sleep(sleep_time_setting*4)
        else:
            logging.exception(msg=('Exception:', e))
            if "RateLimitExceeded" in str(e):
                logging.info(msg=('RATE LIMIT EXCEEDED : ', str(e)))
                sleep(round(sleep_time_setting*2))

            if "HTTP Error 403" in str(e):
                logging.warning('Probably banned from %s' % subreddit_from_submission)
                add_bad_subreddit(str(subreddit_from_submission))
            pass

    if len(comments_already_done) >= 2500 or len(posts_already_done) >= 2500:
        cleanup_memory_usage()
        sleep(round(sleep_time_setting*4))

    if posted_this_iteration:
        posted_this_iteration = False
        sleep()
    else:
        sleep(10)
