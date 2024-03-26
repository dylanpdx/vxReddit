import base64
from urllib.parse import quote

def fixUrlForDiscord(url):
    # convert url to base64
    url = base64.b64encode(url.encode()).decode()
    # url encode
    url = quote(url,safe='')
    return f'https://redirect.dylanpdx.workers.dev/{url}' # TODO: don't hardcode this