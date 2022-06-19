from dotenv import load_dotenv
import os
import time
import tweepy
from tweepy import TweepyException
import logging
import requests

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("bot.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def authentication(api_version="v1"):
    assert (
        api_version == "v1" or api_version == "v2"
    ), "api_version keyword argument should be v1 or v2"
    try:
        if api_version == "v1":
            twitter_auth = tweepy.OAuthHandler(
                os.environ["TWITTER_API_KEY"], os.environ["TWITTER_API_KEY_SECRET"]
            )
            twitter_auth.set_access_token(
                os.environ["TWITTER_ACCESS_TOKEN"],
                os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
            )
            api = tweepy.API(twitter_auth)

        elif api_version == "v2":
            api = tweepy.Client(
                bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
                consumer_key=os.environ["TWITTER_OAUTH2_CLIENT_ID"],
                consumer_secret=os.environ["TWITTER_OAUTH2_CLIENT_SECRET"],
                access_token=os.environ["TWITTER_ACCESS_TOKEN"],
                access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
            )

    except Exception as e:
        logger.debug("Twitter api could not be initialised, reason..", e)
        raise

    else:
        return api


def manipulate_file(mode, text=None):

    try:
        current_directory = os.path.abspath(
            os.path.dirname(__file__)
        )  # if this doesn't work change back to os.getcwd()
        since_id_file_path = os.path.join(current_directory, "since_id.txt")
        if mode == "w":
            if text is not None:
                with open(since_id_file_path, mode="w") as file:
                    file.write(str(text))
                    return
            return
        elif mode == "r":
            # if file exists then read from file, if not return None
            if os.path.exists(since_id_file_path):
                with open(since_id_file_path, mode="r") as file:
                    file.read()
                    return
            return None
    except (OSError, Exception) as e:
        logger.debug("Trouble with since_id file handling..", e)
        raise


def get_timeline_mentions(twitter_api):
    since_id = manipulate_file("r")
    try:
        mentions = (
            [
                status
                for status in tweepy.Cursor(
                    twitter_api.mentions_timeline, since_id=int(since_id)
                ).items()
            ]
            if since_id
            else [
                status
                for status in tweepy.Cursor(twitter_api.mentions_timeline).items()
            ]
        )
    except TweepyException as e:
        logger.debug("Trouble with timeline_mentions...", e)
        raise

    since_id = mentions[0].id if len(mentions) > 0 else since_id
    manipulate_file("w", text=since_id)
    return mentions


def reply_mentions_with_coconut_url(twitter_api, status_id):
    coconut_url = f"http://localhost/?twitter_media_id={media_id}"
    twitter_api.update_status(
        f"hey link here {coconut_url}", in_reply_to_status_id=status_id
    )


def store_image(twitter_api, tweet_id):

    # include entitites attaches media_urls to tweet objects
    tweet = twitter_api.get_status(tweet_id, include_entities=True)
    try:
        image_url = tweet["entities"]["extended_entities"]["media"][0]["media_url"]
    except (KeyError, IndexError):
        image_url = None

    if image_url is not None:
        try:
            image = requests.get(image_url, stream=True)
            image.raise_for_status()
            # saving the images locally for  now
            images_path = os.path.join(os.getcwd(), "images")
            if not os.path.exists(images_path):
                os.mkdir("images")
            image_file_path = os.path.join(images_path, image_url)
            with open(image_file_path, mode="wb") as image_file:
                image_file.write(image.content)
                logger.info(f"Image successfully saved..{image_url}")
            return True

        except Exception as e:
            logger.debug("Image could not be downloaded...", e)
            # need to do something better here
            return False
    else:
        return False


def main(wait_time=10):
    api = authentication()

    while True:
        bot_mentions = get_timeline_mentions(api)
        for status in reversed(bot_mentions):
            status_id_replied = status.in_reply_to_status_id
            if store_image(api, status_id_replied):
                reply_mentions_with_coconut_url(api, status.id)

        time.sleep(wait_time)


if __name__ == "__main__":
    main()
