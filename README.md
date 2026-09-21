# vxreddit
Basic website that serves Reddit posts with actual working embeds to various platforms (Discord, Telegram, etc.) by using Reddit's API.

## How to use the hosted version

Just replace reddit.com with vxreddit.com on the link to the Reddit post: `https://www.reddit.com/r/subreddit/comments/postid/title` -> `https://vxreddit.com/r/subreddit/comments/postid/title`

## Limitations
- Without a proper API key, the application relies on Reddit's JSON API, which may change or be removed.
- Video conversion may require additional setup if not using the local option.

## Extras
- You can add ?legacy or ?l to use the old version of embeds before [the changes done on Sep. 18](https://github.com/dylanpdx/vxReddit/commit/951511be8d527c3bdfa22ce69cfa404cf84f4e09). This affects only Discord.