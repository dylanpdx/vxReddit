import base64
import os
import subprocess
import tempfile

def generateVideo(videoUrl,audioUrl):
    with tempfile.TemporaryDirectory() as tmpdirname:
        # combine video and audio into one file using ffmpeg
        subprocess.run(["ffmpeg", "-i", videoUrl, "-i", audioUrl, "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", f"{tmpdirname}/combined.mp4"], capture_output=True)
        # encode video to base64
        with open(f"{tmpdirname}/combined.mp4", "rb") as videoFile:
            encoded_string = base64.b64encode(videoFile.read())
    return encoded_string