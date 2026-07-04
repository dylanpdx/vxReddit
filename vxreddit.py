import base64
import io
import os
import re
import urllib.parse

import m3u8
import praw
import prawcore
import requests
from flask import Flask, abort, redirect, render_template, request, send_file
from flask_cors import CORS

import config
import videoCombiner

app = Flask(__name__)
CORS(app)

"""
facebookexternalhit/1.1
Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36
Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/1596241936; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36
Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0
facebookexternalhit/1.1
Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; Valve Steam FriendsUI Tenfoot/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36
Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:38.0) Gecko/20100101 Firefox/38.0
Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)
TelegramBot (like TwitterBot)
Mozilla/5.0 (compatible; January/1.0; +https://gitlab.insrt.uk/revolt/january)
test
"""

r_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Cookie": os.environ.get("REDDIT_COOKIE"),
}


def get_video_urls(post_info):
    reddit_video = post_info["media"]["reddit_video"]

    if reddit_video["is_gif"] or not reddit_video.get("has_audio", True):
        return reddit_video["fallback_url"], None

    hls_url = reddit_video["hls_url"]
    base_url = hls_url[: hls_url.rfind("/") + 1]

    playlist = m3u8.load(hls_url)

    video = max(playlist.playlists, key=lambda p: p.stream_info.bandwidth or 0)

    audio = next(
        (
            m
            for m in playlist.media
            if m.type == "AUDIO" and m.group_id == video.stream_info.audio
        ),
        None,
    )

    if audio is None:
        return reddit_video["fallback_url"], None
    else:
        return base_url + video.uri, base_url + audio.uri


def get_image_urls(post_info):
    images = []

    for media in post_info["gallery_data"]["items"]:
        image = post_info["media_metadata"][media["media_id"]]

        if image["status"] != "valid":
            continue

        original = image["s"]
        match image["e"]:
            case "Image":
                url = original["u"]
                url = url.replace("https://preview.redd.it/", "https://i.redd.it/")
                url = url.split("?")[0]
                images.append(url)
            case "AnimatedImage":
                url = original["gif"]
                images.append(url)

    return images


def embed_info_from_post(post_info):
    match post_info.get("post_hint"):
        case None:
            if post_info.get("removed_by_category"):
                post_type = "text"
            elif post_info.get("gallery_data"):
                post_type = "gallery"
            elif not post_info.get("url"):
                post_type = "text"
            elif post_info["url"].startswith(("/", "https://www.reddit.com/")):
                post_type = "text"
            else:
                post_type = "link"
        case "image":
            post_type = "image"
        case "hosted:video":
            post_type = "video"
        case "link" | "rich:video":
            post_type = "link"
        case "self":
            post_type = "text"
        case _:
            post_type = "unknown"

    embed_info = {
        "post_type": post_type,
        "title": post_info["title"].strip(),
        "author": post_info["author"],
        "subreddit": post_info["subreddit_name_prefixed"],
        "upvotes": post_info["ups"],
        "comments": post_info.get("num_comments", None),
    }

    if "selftext" in post_info:
        embed_info["text"] = post_info["selftext"]
    else:
        embed_info["text"] = post_info["body"]

    embed_info["text"] = embed_info["text"].strip()

    if post_type == "video":
        video_url, audio_url = get_video_urls(post_info)

        embed_info["video_url"] = video_url
        embed_info["video_width"] = post_info["media"]["reddit_video"]["width"]
        embed_info["video_height"] = post_info["media"]["reddit_video"]["height"]

        embed_info["audio_url"] = audio_url

        embed_info["thumbnail_url"] = post_info["preview"]["images"][0]["source"]["url"]
    elif post_type == "image":
        embed_info["images"] = [post_info["url"]]
    elif post_type == "gallery":
        embed_info["images"] = get_image_urls(post_info)
    elif embed_info["post_type"] == "link":
        url = post_info["url"]
        embed_info["text"] = f"{url}\n\n{embed_info['text']}"

        if "preview" in post_info:
            embed_info["thumbnail_url"] = post_info["preview"]["images"][0]["source"][
                "url"
            ]
        elif post_info["thumbnail"].startswith("https://"):
            embed_info["thumbnail_url"] = post_info["thumbnail"]

    return embed_info


def get_embed_info_from_url(post_id, comment_id):
    json_url = id_to_url(post_id, comment_id) + ".json?raw_json=1"
    r = requests.get(json_url, headers=r_headers)

    if r.status_code != 200:
        return None

    response = r.json()

    post_info = response[0]["data"]["children"][0]["data"]

    if comment_id:
        post_replies = response[1]["data"]["children"]

        new_title = "RE: " + post_info["title"]
        post_info = post_replies[0]["data"]
        post_info["title"] = new_title

    if not post_info:
        return None

    return embed_info_from_post(post_info)


def get_embed_info_from_url_praw(post_id, comment_id):
    client_id = config.currentConfig["MAIN"]["praw_client_id"]
    client_secret = config.currentConfig["MAIN"]["praw_client_secret"]
    user_agent = config.currentConfig["MAIN"]["praw_user_agent"]

    if not (client_id and client_secret and user_agent):
        return None

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    post_info = {}

    if comment_id:
        post = reddit.comment(id=comment_id)
    else:
        post = reddit.submission(id=post_id)

    try:
        post._fetch()
    except prawcore.Forbidden:
        return None

    if comment_id:
        post_info["title"] = "RE: " + post.submission.title
        post_info["body"] = post.body
    else:
        post_info |= {
            "title": post.title,
            "selftext": post.selftext,
            "num_comments": post.num_comments,
            "url": post.url,
            "thumbnail": post.thumbnail,
            "removed_by_category": post.removed_by_category,
        }

    author = post.author
    if not author:
        author = "[deleted]"
    else:
        author = post.author.name

    post_info |= {
        "author": author,
        "subreddit_name_prefixed": post.subreddit_name_prefixed,
        "ups": post.ups,
    }

    if hasattr(post, "gallery_data"):
        post_info["gallery_data"] = post.gallery_data
        post_info["media_metadata"] = post.media_metadata
    if hasattr(post, "media"):
        post_info["media"] = post.media
    if hasattr(post, "preview"):
        post_info["preview"] = post.preview
    if hasattr(post, "post_hint"):
        post_info["post_hint"] = post.post_hint

    return embed_info_from_post(post_info)


def build_stats_line(embed_info):
    author = embed_info["author"]
    subreddit = embed_info["subreddit"]
    upvotes = embed_info["upvotes"]
    stats_line = f"u/{author} on {subreddit} - ⬆️ {upvotes}"

    comments = embed_info["comments"]
    if comments is not None:
        stats_line += f" | 💬 {comments}"

    return stats_line


@app.route("/redditvideo.mp4")
def get_video():
    video_url = request.args.get("video_url", "")
    audio_url = request.args.get("audio_url", "")

    if not video_url:
        abort(400)

    if not video_url.startswith("https://v.redd.it/") or not audio_url.startswith(
        "https://v.redd.it/"
    ):
        abort(400)

    if not audio_url:
        return redirect(video_url)

    if config.currentConfig["MAIN"]["videoConversion"] == "local":
        b64 = videoCombiner.generateVideo(video_url, audio_url)

        return send_file(io.BytesIO(base64.b64decode(b64)), mimetype="video/mp4")
    else:
        renderer = config.currentConfig["MAIN"]["videoConversion"]

        video_url = urllib.parse.quote(video_url, safe="")
        audio_url = urllib.parse.quote(audio_url, safe="")

        return redirect(
            f"{renderer}?video_url={video_url}&audio_url={audio_url}", code=307
        )


def get_embed_info(post_id, comment_id):
    embed_info = get_embed_info_from_url_praw(post_id, comment_id)
    if embed_info:
        return embed_info

    embed_info = get_embed_info_from_url(post_id, comment_id)
    if embed_info:
        return embed_info

    return None


def embed_reddit(post_id, comment_id):
    if post_id is None:
        abort(404)

    args = {
        "app_name": config.currentConfig["MAIN"]["appName"],
        "domain_name": config.currentConfig["MAIN"]["domainName"],
        "embed_color": config.currentConfig["MAIN"]["embedColor"],
        "redirect_url": id_to_url(post_id, comment_id),
    }

    try:
        embed_info = get_embed_info(post_id, comment_id)
    except Exception as e:
        return render_template(
            "message.html",
            message=f"Internal server error: {type(e).__name__}: {e}",
            **args,
        )

    if not embed_info:
        return render_template(
            "message.html",
            message="Failed to get data from Reddit",
            **args,
        )

    args |= {
        "embed_info": embed_info,
        "stats_line": build_stats_line(embed_info),
    }

    if embed_info["post_type"] in ("text", "link"):
        return render_template("text.html", **args)
    elif embed_info["post_type"] in ("image", "gallery"):
        return render_template("image.html", **args)
    elif embed_info["post_type"] == "video":
        if not embed_info["audio_url"]:
            converted_url = embed_info["video_url"]
        else:
            video_url = urllib.parse.quote(embed_info["video_url"], safe="")
            audio_url = urllib.parse.quote(embed_info["audio_url"], safe="")
            converted_url = (
                "https://"
                + config.currentConfig["MAIN"]["domainName"]
                + "/redditvideo.mp4?video_url="
                + video_url
                + "&audio_url="
                + audio_url
            )
        return render_template("video.html", video_url=converted_url, **args)
    else:
        return render_template(
            "message.html",
            message="Unknown post type",
            **args,
        )


@app.route("/")
def main():
    return redirect(config.currentConfig["MAIN"]["repoURL"])


@app.route("/oembed")
def alternateJSON():
    return {
        "type": "link",
        "version": "1.0",
        "title": "vxReddit",
        "author_name": request.args.get("text"),
        "author_url": request.args.get("url"),
        "provider_name": config.currentConfig["MAIN"]["appName"],
        "provider_url": config.currentConfig["MAIN"]["repoURL"],
    }


def id_to_url(post_id, comment_id):
    post_link = f"https://www.reddit.com/comments/{post_id}"
    if comment_id:
        post_link += f"/_/{comment_id}"

    return post_link


def clean_path(path):
    path = path.split("?")[0]
    path = re.sub(r"/{2,}", "/", path)

    path = path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path

    return path


def validate_path(path):
    id_re = r"(?-i:[0-9a-z]+)"
    share_id_re = r"(?-i:[0-9A-Za-z]{10})"

    subreddit_or_user = r"(?:r|u|user)/[^/]+"

    # /comments/[p]
    # /comments/[p]/[]
    # /comments/[p]/[]/[c]
    # /r/[]/comments/[p]
    # /r/[]/comments/[p]/[]
    # /r/[]/comments/[p]/[]/[c]
    # or with /u/, /user/, or /r/u_ instead of /r/
    full = re.compile(
        rf"^(?:/{subreddit_or_user})?/comments/({id_re})(?:/[^/]+(?:/({id_re}))?)?$",
        re.IGNORECASE,
    )

    # /[p] (redd.it)
    short = re.compile(rf"^/({id_re})$")

    # /r/[]/s/[s]
    share = re.compile(
        rf"^/{subreddit_or_user}/s/{share_id_re}$",
        re.IGNORECASE,
    )

    match = share.match(path)
    if match:
        r = requests.head(
            f"https://www.reddit.com{path}", allow_redirects=True, headers=r_headers
        )
        path = clean_path(urllib.parse.urlparse(r.url).path)

    match = full.match(path)
    if match:
        return match.group(1), match.group(2)

    match = short.match(path)
    if match:
        return match.group(1), None

    return None, None


@app.route("/<path:path>")
def embedReddit(path):
    path = clean_path(path)

    post_id, comment_id = validate_path(path)

    return embed_reddit(post_id, comment_id)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
