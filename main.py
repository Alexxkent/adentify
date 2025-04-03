import scripts
import os
import identify_logo
import parse_video
import segment_video
import gui
import threading

path_to_add = scripts.resource_path("ffmpeg/bin")
original_path = os.environ.get('PATH', '')
os.environ['PATH'] = path_to_add + os.pathsep + original_path
already_running = threading.Event()


def identify_process(video_path, output_path, model_output_path, channel, date, update_queue):
    scene_list = parse_video.parse_scene(video_path, update_queue)
    audio_list = parse_video.parse_audio(video_path, update_queue)
    transitions = segment_video.get_scene_changes_in_silence(scene_list, audio_list, update_queue)
    dirty_segmented_video = segment_video.classify_video(transitions)
    segmented_video = segment_video.adjust_segmented_video(scene_list, dirty_segmented_video, update_queue)
    blocks = identify_logo.get_logos(segmented_video, video_path, model_output_path, update_queue)
    xlsx_name = scripts.generate_results(blocks, output_path, channel, date)
    update_queue.put(f'process6-{xlsx_name}')
    os.environ['PATH'] = original_path


def main():
    global already_running
    if already_running.is_set():
        return
    already_running.set()

    try:
        # Launch the GUI
        gui.show_main_screen(None, None)
    except Exception as e:
        scripts.show_error(e)


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
