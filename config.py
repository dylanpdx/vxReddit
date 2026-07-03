import configparser
import os

currentConfig = configparser.ConfigParser()

## default values

currentConfig["MAIN"] = {
    "appName": "vxReddit",
    "embedColor": "#FF4500",
    "repoURL": "https://github.com/dylanpdx/vxReddit",
    "domainName": "vxreddit.com",
    "videoConversion": "local",
    "praw_client_id": "",
    "praw_client_secret": "",
    "praw_user_agent": "",
}

if "RUNNING_SERVERLESS" in os.environ and os.environ["RUNNING_SERVERLESS"] == "1":
    currentConfig["MAIN"] = {
        "appName": os.environ["APP_NAME"],
        "embedColor": os.environ["EMBED_COLOR"],
        "repoURL": os.environ["REPO_URL"],
        "domainName": os.environ["DOMAINNAME"],
        "videoConversion": os.environ["VIDEOCONVERSION"],
        "praw_client_id": os.getenv("PRAW_CLIENT_ID", ""),
        "praw_client_secret": os.getenv("PRAW_CLIENT_SECRET", ""),
        "praw_user_agent": os.getenv("PRAW_USER_AGENT", ""),
    }
else:
    if os.path.exists("vxReddit.conf"):
        # as per python docs, "the most recently added configuration has the highest priority"
        # "conflicting keys are taken from the more recent configuration while the previously existing keys are retained"
        currentConfig.read("vxReddit.conf")

    with open("vxReddit.conf", "w") as configfile:
        currentConfig.write(configfile)  # write current config to file
