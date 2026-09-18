def build_stats_line(embed_info):
    author = embed_info["author"]
    subreddit = embed_info["subreddit"]
    upvotes = embed_info["upvotes"]
    stats_line = f"u/{author} on {subreddit} - ⬆️ {upvotes}"

    comments = embed_info["comments"]
    if comments is not None:
        stats_line += f" | 💬 {comments}"

    return stats_line