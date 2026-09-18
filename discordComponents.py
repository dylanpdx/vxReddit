import config 
from utils import build_stats_line
media_per_post = 10

def build_text_components(embed_info,post_url):
    component = {
        "component":{
            "type":17,
            "accent_color": int(config.currentConfig["MAIN"]["embedcolor"].replace("#","0x"),16),
            "components":[
                {
                    "type":10,
                    "content":'-# '+config.currentConfig["MAIN"]["appName"]
                },
                {
                    "type":10,
                    "content":f'** {build_stats_line(embed_info)} [(link)]({post_url}) **'
                },
                {
                    "type":10,
                    "content":f"## {embed_info['title']}"
                },
                {
                    "type":10,
                    "content":f'{embed_info["text"]}'
                }
            ]
        }
    }
    return component

def build_image_components(embed_info,post_url):
    component = build_text_components(embed_info,post_url)

    media = []
    for image in embed_info["images"]:
        media.append({"media":{"url":image}})
    if len(media) > media_per_post:
        media = media[:media_per_post]

    component["component"]["components"].append({
        "type":12,
        "items":media
    })

    return component

def build_components(embed_info,post_url):
    if embed_info["post_type"] in ("image", "gallery"):
        return build_image_components(embed_info,post_url)
    elif embed_info["post_type"] in ("text", "link"):
        return build_text_components(embed_info,post_url)
    return None