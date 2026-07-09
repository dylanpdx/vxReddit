import base64
import os
import subprocess
import tempfile
import time


def ffmpeg(args):
    start = time.time()

    with tempfile.TemporaryDirectory() as tempdir:
        new_path = os.path.join(tempdir, "combined.mp4")

        args.insert(0, "ffmpeg")
        args.append(new_path)

        res = subprocess.run(args, capture_output=True)

        if res.returncode == 0:
            with open(new_path, "rb") as f:
                encoded_string = base64.b64encode(f.read())
        else:
            encoded_string = None

    end = time.time()

    print(f"Video generation took {end - start} seconds")

    return encoded_string


def combine_videos(video_url, audio_url):
    return ffmpeg(
        [
            "-i",
            video_url,
            "-i",
            audio_url,
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
        ]
    )


def video_from_id(id):
    return ffmpeg(["-i", f"https://v.redd.it/{id}/DASHPlaylist.mpd", "-c", "copy"])
