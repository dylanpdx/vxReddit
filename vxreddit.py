from flask import Flask, render_template, request, redirect, send_file, abort
from flask_cors import CORS
import config
import requests
import videoCombiner
import base64
import io
import urllib.parse
app = Flask(__name__)
CORS(app)
import os
from discordWorkaround import fixUrlForDiscord

embed_user_agents = [
    "facebookexternalhit/1.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/1596241936; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0",
    "facebookexternalhit/1.1",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; Valve Steam FriendsUI Tenfoot/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:38.0) Gecko/20100101 Firefox/38.0",
    "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "TelegramBot (like TwitterBot)",
    "Mozilla/5.0 (compatible; January/1.0; +https://gitlab.insrt.uk/revolt/january)",
    "test"]


r_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"}

if os.environ.get('REDDIT_COOKIE') is not None:
    r_headers['cookie'] = os.environ.get('REDDIT_COOKIE')

def message(text):
    return render_template(
        'message.html', 
        message=text, 
        appname=config.currentConfig["MAIN"]["appName"]
    )

def getVideoFromPostURL(url):
    url = url+".json"
    
    response = requests.get(url,headers=r_headers)
    if response.status_code != 200:
        return None
    resp=response.json()
    post_info = resp[0]["data"]["children"][0]["data"]

    # determine post type (video, image, text, gif, link, image gallery)
    post_type = "unknown"
    if "media_metadata" in post_info:
        post_type = "gallery"
    elif "url" in post_info and post_info["url"].endswith((".jpg",".png",".gif",".jpeg")):
        post_type = "image"
    elif ("is_video" in post_info and post_info["is_video"]) or ("post_hint" in post_info and post_info["post_hint"] == "hosted:video"):
        post_type = "video"
    elif "url_overridden_by_dest" in post_info:
        post_type = "link"
    elif "selftext" in post_info and post_info["selftext"] != "":
        post_type = "text"

    if not post_info:
        return None

    vxData = {
        "post_type": post_type,
        "title": post_info["title"],
        "author": post_info["author"],
        "subreddit": post_info["subreddit_name_prefixed"],
        "permalink": post_info["permalink"],
        "url": post_info["url"],
        "upvotes": post_info["ups"],
        "comments": post_info["num_comments"],
        "awards": post_info["total_awards_received"],
        "created": post_info["created_utc"],
        "permalink": "https://www.reddit.com"+post_info["permalink"]
    }

    if (post_type == "video"):
        vxData["video_url"] = post_info["media"]["reddit_video"]["fallback_url"]
        vxData["video_width"] = post_info["media"]["reddit_video"]["width"]
        vxData["video_height"] = post_info["media"]["reddit_video"]["height"]
        # get audio url
        audio_url = None
        if "has_audio" in post_info["media"]["reddit_video"] and not post_info["media"]["reddit_video"]["has_audio"]:
            audio_url = None
        else:
            for url in ['DASH_AUDIO_128.mp4','DASH_audio.mp4']:
                testUrl = post_info["media"]["reddit_video"]["fallback_url"].split("DASH_")[0]+url
                if requests.head(testUrl).status_code == 200:
                    audio_url = testUrl
                    break
        vxData["audio_url"] = audio_url
        # get thumbnail
        if 'preview' in post_info:
            vxData["thumbnail_url"] = post_info["preview"]["images"][0]["source"]["url"].replace("&amp;","&")
        else:
            vxData["thumbnail_url"] = post_info["thumbnail"]
    elif (post_type == "image"):
        vxData["images"] = [post_info["url"]]
        # get thumbnail
        vxData["thumbnail_url"] = post_info["thumbnail"]
    elif (post_type == "gallery"):
        vxData["images"] = []
        for image in post_info["media_metadata"]:
            postUrl = post_info["media_metadata"][image]["s"]["u"]
            if postUrl.startswith("https://preview.redd.it"):
                postUrl = postUrl.replace("https://preview.redd.it","https://i.redd.it")
            vxData["images"].append(postUrl)
        # get thumbnail
        vxData["thumbnail_url"] = post_info["thumbnail"]
    #elif (post_type == "link"):
        #vxData["link_url"] = post_info["url_overridden_by_dest"]
        # get thumbnail
        #vxData["thumbnail_url"] = post_info["thumbnail"]
    else:
        vxData["text"] = post_info["selftext"]
        # get thumbnail
        vxData["thumbnail_url"] = post_info["thumbnail"]
        if vxData["text"] == "" and vxData["title"] != "":
            vxData["text"] = post_info["title"]
        if vxData["post_type"] == "link" and vxData["url"] != "":
            url=vxData["url"]
            vxData["text"] = f"【🌐 {url} 】\n\n"+vxData['text']

    
    return vxData

def build_stats_line(post_info):
    upvotes = post_info["upvotes"]
    comments = post_info["comments"]
    awards = post_info["awards"]
    stats_line = f"⬆️ {upvotes} | 💬 {comments} | 🏆 {awards}"
    return stats_line

@app.route('/redditvideo.mp4')
def get_video():
    # get video_url and audio_url from query string
    video_url = request.args.get('video_url')
    audio_url = request.args.get('audio_url')
    if video_url is None:
        abort (400)
    # check if video_url and audio_url are valid
    if not video_url.startswith("https://v.redd.it/") or (audio_url is not None and not audio_url.startswith("https://v.redd.it/")):
        abort (400)
    if audio_url is None:
        return redirect(video_url)
    if config.currentConfig["MAIN"]["videoConversion"] == "local":
        # combine video and audio into one file using ffmpeg
        b64 = videoCombiner.generateVideo(video_url,audio_url)
        # return video file
        return send_file(io.BytesIO(base64.b64decode(b64)), mimetype='video/mp4')
    else:
        renderer=config.currentConfig["MAIN"]["videoConversion"]
        # url encode video_url and audio_url
        video_url = urllib.parse.quote(video_url, safe='')
        audio_url = urllib.parse.quote(audio_url, safe='')
        return redirect(f"{renderer}?video_url={video_url}&audio_url={audio_url}",code=307)

def embed_reddit(post_link,isDiscordBot=False):
    videoInfo = getVideoFromPostURL(post_link)
    if videoInfo is None:
        return message("Failed to get data from Reddit")
    statsLine = build_stats_line(videoInfo)
    if videoInfo["post_type"] == "unknown":
        return message("Unknown post type")
    elif videoInfo["post_type"] == "text" or videoInfo["post_type"] == "link":
        return render_template("text.html", vxData=videoInfo,appname=config.currentConfig["MAIN"]["appName"], statsLine=statsLine, domainName=config.currentConfig["MAIN"]["domainName"])
    elif videoInfo["post_type"] == "image":
        return render_template("image.html", vxData=videoInfo,appname=config.currentConfig["MAIN"]["appName"], statsLine=statsLine, domainName=config.currentConfig["MAIN"]["domainName"])
    elif videoInfo["post_type"] == "gallery":
        imageCount = str(len(videoInfo["images"]))
        return render_template("image.html", vxData=videoInfo,appname=config.currentConfig["MAIN"]["appName"]+" - Gallery with "+imageCount+" image(s)", statsLine=statsLine, domainName=config.currentConfig["MAIN"]["domainName"])
    #elif videoInfo["post_type"] == "link":
    #    return redirect(videoInfo["link_url"]) # this might need to be improved later
    elif videoInfo["post_type"] == "video":
        if videoInfo["audio_url"] is None:
            convertedUrl = videoInfo["video_url"]
        else:
            encodedVideoURL = urllib.parse.quote(videoInfo["video_url"], safe='')
            encodedAudioURL = urllib.parse.quote(videoInfo["audio_url"], safe='')
            convertedUrl = "https://"+config.currentConfig["MAIN"]["domainName"]+"/redditvideo.mp4?video_url="+encodedVideoURL+"&audio_url="+encodedAudioURL
        if isDiscordBot:
            convertedUrl = fixUrlForDiscord(convertedUrl)
        return render_template("video.html", vxData=videoInfo,appname=config.currentConfig["MAIN"]["appName"], statsLine=statsLine, domainName=config.currentConfig["MAIN"]["domainName"],mp4URL=convertedUrl)
    else:
        return videoInfo

@app.route('/')
def main():
    return redirect(config.currentConfig["MAIN"]["repoURL"])

@app.route('/owoembed')
def alternateJSON():
    return {
        "author_name": request.args.get('text'),
        "author_url": request.args.get('url'),
        "provider_name": request.args.get('provider_name'),
        "provider_url": config.currentConfig["MAIN"]["repoURL"],
        "title": "Reddit",
        "type": "link",
        "version": "1.0"
    }


@app.route('/<path:sub_path>')
def embedReddit(sub_path):
    user_agent = request.headers.get('user-agent')
    post_link = "https://www.reddit.com/" + sub_path

    r = requests.get(post_link, allow_redirects=False, headers=r_headers)
    if 'location' in r.headers and r.headers['location'].startswith("https"):
        post_link = r.headers['location']
    if "?" in post_link:
        post_link = post_link.split("?")[0]
    
    return embed_reddit(post_link,'Discordbot' in user_agent)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
