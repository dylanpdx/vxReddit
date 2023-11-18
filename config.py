import configparser
import os

currentConfig = configparser.ConfigParser()

## default values

currentConfig["MAIN"]={
    "appName": "vxReddit",
    "embedColor": "#EE1D52",
    "repoURL":"https://github.com/dylanpdx/vxReddit",
    "domainName":"vxreddit.com",
    "videoConversion":"local",
}

if 'RUNNING_SERVERLESS' in os.environ and os.environ['RUNNING_SERVERLESS'] == '1':
    currentConfig["MAIN"]={
        "appName": os.environ['APP_NAME'],
        "embedColor": "#EE1D52",
        "repoURL":os.environ['REPO_URL'],
        "domainName":os.environ['DOMAINNAME'],
        "videoConversion":os.environ['VIDEOCONVERSION'],
    }
else:
    if os.path.exists("vxReddit.conf"):
        # as per python docs, "the most recently added configuration has the highest priority"
        # "conflicting keys are taken from the more recent configuration while the previously existing keys are retained"
        currentConfig.read("vxReddit.conf")

    with open("vxReddit.conf", "w") as configfile:
        currentConfig.write(configfile) # write current config to file