import configparser
import os

currentConfig = configparser.ConfigParser()

# default values

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


def config_default(var, config_key, required=False):
    if required:
        currentConfig["MAIN"][config_key] = os.environ[var]
    else:
        currentConfig["MAIN"][config_key] = os.getenv(
            var, currentConfig["MAIN"][config_key]
        )


if os.getenv("RUNNING_SERVERLESS") == "1":
    config_default("APP_NAME", "appName")
    config_default("EMBED_COLOR", "embedColor")
    config_default("REPO_URL", "repoURL")
    config_default("VIDEOCONVERSION", "videoConversion")
    config_default("PRAW_CLIENT_ID", "praw_client_id")
    config_default("PRAW_CLIENT_SECRET", "praw_client_secret")
    config_default("PRAW_USER_AGENT", "praw_user_agent")

    config_default("DOMAINNAME", "domainName", True)
else:
    if os.path.exists("vxReddit.conf"):
        # as per python docs, "the most recently added configuration has the highest priority"
        # "conflicting keys are taken from the more recent configuration while the previously existing keys are retained"
        currentConfig.read("vxReddit.conf")

    with open("vxReddit.conf", "w") as configfile:
        currentConfig.write(configfile)  # write current config to file
