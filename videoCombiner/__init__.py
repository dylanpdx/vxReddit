import base64
import subprocess
import tempfile
import os
import time

def generateVideo(videoUrl,audioUrl):
    start = time.time()
    with tempfile.TemporaryDirectory() as tmpdirname:
        newPath = os.path.join(tmpdirname, "combined.mp4")
        # combine video and audio into one file using ffmpeg
        subprocess.run(["ffmpeg", "-i", videoUrl, "-i", audioUrl, "-c:v", "copy", "-c:a", "copy", "-map", "0:v:0", "-map", "1:a:0", newPath], capture_output=True)
        # encode video to base64
        with open(newPath, "rb") as videoFile:
            encoded_string = base64.b64encode(videoFile.read())
    end = time.time()
    print(f"Video generation took {end - start} seconds")
    return encoded_string