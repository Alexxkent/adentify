import cv2
import subprocess
from pydub import AudioSegment, silence
from scenedetect import VideoManager, SceneManager, StatsManager
from scenedetect.detectors import AdaptiveDetector
import scripts
import sys
import os
import warnings


def get_frame_at_timestamp(timestamp, video_path):
    # Open the video file
    cap = cv2.VideoCapture(video_path)

    # Get the frame rate of the video
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Calculate the frame number corresponding to the timestamp
    frame_number = int(timestamp * fps)

    # Set the video capture object to the calculated frame number
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    # Read the frame at the calculated frame number
    ret, frame = cap.read()

    # Release the video capture object
    cap.release()

    # Check if frame is successfully read
    if ret:
        return frame
    else:
        scripts.show_error("Failed to retrieve frame at timestamp:", timestamp)
        return None


# this returns a list of timestamps of
def parse_scene(video_path, update_queue):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)

        # Redirect stderr temporarily
        old_stderr = sys.stderr
        sys.stderr = open(os.devnull, "w")

        try:
            video_manager = VideoManager([video_path])
            stats_manager = StatsManager()
            scene_manager = SceneManager(stats_manager)

            scene_manager.add_detector(AdaptiveDetector(adaptive_threshold=1.8))

            video_manager.set_downscale_factor()
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)

        finally:
            # Restore stderr
            sys.stderr.close()
            sys.stderr = old_stderr

        scene_list = scene_manager.get_scene_list()
        scene_times = list()

        for scene in scene_list:
            start, end = scene
            scene_times.append((start.get_seconds(), end.get_seconds()))

        update_queue.put('process1')
        return scene_times


def parse_audio(video_path, update_queue):
    convert_mkv_to_mp3(video_path, scripts.resource_path("temp.mp3"))

    audio = AudioSegment.from_mp3(scripts.resource_path("temp.mp3"))
    silent_ranges = silence.detect_silence(audio, min_silence_len=125, silence_thresh=-42) # 500, -38 works for sample. 50 -50 works for small big, 200 -40 works for sample
    silent_ranges = [(start/1000, end/1000) for start, end in silent_ranges]  # convert to seconds
    update_queue.put('process2')

    return silent_ranges


def parse_audio_between(start_time, end_time):
    # Load audio file
    audio = AudioSegment.from_file(scripts.resource_path("temp.mp3"))

    # Convert time to milliseconds
    start_time = start_time * 1000
    end_time = end_time * 1000

    # Extract portion of audio
    extracted_audio = audio[start_time:end_time]

    silent_ranges = silence.detect_silence(extracted_audio, min_silence_len=125, silence_thresh=-35) # 500, -38 works for sample. 50 -50 works for small big, 200 -40 works for sample
    silent_ranges = [(start/1000, end/1000) for start, end in silent_ranges]  # convert to seconds

    return silent_ranges


def convert_mkv_to_mp3(input_file, output_file):
    command = ["ffmpeg", "-y", "-i", input_file, "-vn", "-c:a", "libmp3lame", output_file]
    try:
        print(f"Running command: {' '.join(command)}")  # Debugging: Print the command
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")