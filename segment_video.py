import os
import subprocess
import parse_video
import scripts

vid_len = 0


def get_scene_changes_in_silence(scene_changes, audio_silences, update_queue):
    global vid_len
    program_change = list()
    program_change.append(0)

    for silence in audio_silences:
        for i, scene_change in enumerate(scene_changes):
            if (silence[0] - 0.2) <= scene_change[1] <= (silence[1] + 0.2): # 0.2
                program_change.append(float(scene_change[1]))

    temp_mp3_path = scripts.resource_path("temp.mp3")
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of","default=noprint_wrappers=1:nokey=1", temp_mp3_path]
    output = subprocess.run(command, capture_output=True, text=True, shell=True)
    program_change.append(float(output.stdout.strip()))
    vid_len = float(output.stdout.strip())
    update_queue.put('process3')

    return program_change


def adjust_segmented_video(scene_changes, segmented_video, update_queue):
    ad_lengths = [15, 30, 10]  # Prioritized order
    buffer = 0.067

    for k in range(2):
        count_back = k == 0
        i = 0
        while i < len(segmented_video):
            seg = segmented_video[i]
            if seg[0] == 'ad':
                i += 1
                continue
            ad_found = False
            program_length = seg[2]

            max_ad_length = max((ad_length for ad_length in ad_lengths if ad_length <= program_length), default=0)

            if max_ad_length == 0:
                i += 1
                continue

            if i == 0 and count_back:
                start = max(0, seg[2] - (max_ad_length + buffer))
                end = seg[2]
            elif 0 < i < len(segmented_video) - 1:
                if count_back:
                    start = max(0, seg[1] + seg[2] - (max_ad_length + buffer))
                    end = seg[1] + seg[2]
                else:
                    start = seg[1]
                    end = seg[1] + (max_ad_length + buffer)
            elif i == len(segmented_video) - 1 and not count_back:
                start = seg[1]
                end = seg[1] + (max_ad_length + buffer)
            else:
                i += 1
                continue
            if count_back:
                start -= 2*buffer
            elif not count_back:
                end += 2*buffer

            transitions = [start]
            audio_silences = parse_video.parse_audio_between(start, end)
            for silence in audio_silences:
                for scene_change in scene_changes:
                    if (silence[0] + start - 0.2) <= scene_change[1] <= (silence[1] + start + 0.2):
                        transitions.append(scene_change[1])
            transitions.append(end)

            durations = get_durations(transitions)
            total_duration = 0

            if count_back:
                for j in range(len(durations) - 1, -1, -1):
                    total_duration += durations[j]
                    if any(abs(total_duration - ad_length) <= buffer for ad_length in ad_lengths):
                        # print(f"Found an ad of duration {total_duration} seconds counting back.")

                        for m in range(len(segmented_video) - 1):
                            if segmented_video[m][1] < transitions[j] < segmented_video[m + 1][1]:
                                new_program_length = segmented_video[m][2] - total_duration
                                segmented_video[m] = (
                                    segmented_video[m][0],
                                    segmented_video[m][1],
                                    new_program_length
                                )
                                segmented_video.insert(m + 1, ('ad', transitions[j], total_duration))
                        ad_found = True
                        break
            else:
                for j in range(len(durations)):
                    total_duration += durations[j]
                    # print(f'dur is {total_duration} at {start}')
                    if any(abs(total_duration - ad_length) <= buffer for ad_length in ad_lengths):
                        new_start = seg[1] + total_duration
                        new_program_length = seg[2] - total_duration
                        segmented_video[i] = (seg[0], new_start, new_program_length)
                        for m in range(len(segmented_video) - 2):  # Adjusted to avoid index errors
                            if segmented_video[m + 1][1] < start < segmented_video[m + 2][1]:
                                segmented_video.insert(m + 2, ('ad', start, total_duration))
                                ad_found = True
                                break
                        if ad_found:
                            break

            if ad_found:
                # Update program length and move to the next segment
                if count_back:
                    new_program_length = seg[2] - total_duration
                    segmented_video[i] = (seg[0], seg[1], new_program_length)

                if new_program_length <= 0:
                    i += 1
            else:
                i += 1

    i = 0
    while i < len(segmented_video):
        if segmented_video[i][0] == 'ad':
            ad_sequence_length = 1
            if i + 1 < len(segmented_video) and segmented_video[i + 1][0] == 'ad':
                ad_sequence_length = 2

            if 0 < i < len(segmented_video) - ad_sequence_length:
                if segmented_video[i - 1][0] == 'program' and segmented_video[i + ad_sequence_length][0] == 'program':
                    new_program_length = (
                        segmented_video[i - 1][2] +
                        sum(segmented_video[i + j][2] for j in range(ad_sequence_length)) +
                        segmented_video[i + ad_sequence_length][2]
                    )
                    segmented_video[i - 1] = (
                        'program',
                        segmented_video[i - 1][1],
                        new_program_length
                    )
                    del segmented_video[i:i + ad_sequence_length + 1]
                    continue
            elif i == 0 and segmented_video[i + ad_sequence_length][0] == 'program':
                new_program_length = (
                    sum(segmented_video[i + j][2] for j in range(ad_sequence_length)) +
                    segmented_video[i + ad_sequence_length][2]
                )
                segmented_video[i + ad_sequence_length] = (
                    'program',
                    segmented_video[i][1],
                    new_program_length
                )
                del segmented_video[i:i + ad_sequence_length]
                continue
            elif i == len(segmented_video) - ad_sequence_length and segmented_video[i - 1][0] == 'program':
                new_program_length = (
                    segmented_video[i - 1][2] +
                    sum(segmented_video[i + j][2] for j in range(ad_sequence_length))
                )
                segmented_video[i - 1] = (
                    'program',
                    segmented_video[i - 1][1],
                    new_program_length
                )
                del segmented_video[i:i + ad_sequence_length]
                continue
        i += 1

    if os.path.exists(scripts.resource_path("temp.mp3")):
        os.remove(scripts.resource_path("temp.mp3"))
    update_queue.put('process4')
    return segmented_video


def next_block_is_ad(starting_index, durations, ad_lengths, buffer):
    i = starting_index
    total_duration = 0

    while i < len(durations) and total_duration < max(ad_lengths) + buffer:
        total_duration += durations[i]
        if any(abs(total_duration - ad_length) <= buffer for ad_length in ad_lengths):
            return True
        i += 1
    return False


def is_within_buffer(value, buffer):
    ad_lengths = [15, 30, 60, 45]

    if any(abs(value - ad_length) <= buffer for ad_length in ad_lengths):
        return True
    else:
        return False


def get_durations(program_change):
    duration_list = list()

    for i in range(1, len(program_change)):
        duration = program_change[i] - program_change[i-1]
        duration_list.append(float(duration))

    return duration_list


def classify_video(transitions):
    buffer = 0.034

    ad_lengths = [15, 30, 60, 45]

    durations = get_durations(transitions)
    combined_transitions = [transitions[0]]
    i = 0
    ad_count = 0
    first_end = None
    first_start = None
    second_end = None
    second_start = None
    old_i = 0
    in_ad_block = False

    while i < len(durations):
        total_duration = 0
        j = i

        while j < len(durations) and total_duration < (max(ad_lengths) + buffer):
            total_duration += durations[j]
            if is_within_buffer(total_duration, buffer):
                # print(f'dur is {total_duration} at transition {transitions[i]}')
                ad_count += 1
                # Append to combined_transitions only if the elements are not already present
                if ad_count > 2:
                    if ad_count == 3:
                        if first_start not in combined_transitions:
                            combined_transitions.append(first_start)
                        if first_end not in combined_transitions:
                            combined_transitions.append(first_end)
                        if second_start not in combined_transitions:
                            combined_transitions.append(second_start)
                        if second_end not in combined_transitions:
                            combined_transitions.append(second_end)
                    if transitions[i] not in combined_transitions:
                        combined_transitions.append(transitions[i])
                    if transitions[j + 1] not in combined_transitions:
                        combined_transitions.append(transitions[j + 1])
                elif ad_count == 1:
                    first_start = transitions[i]
                    first_end = transitions[j + 1]
                    in_ad_block = True
                    old_i = i
                else:
                    second_start = transitions[i]
                    second_end = transitions[j + 1]
                    in_ad_block = True

                i = j
                break
            j += 1
        else:
            in_ad_block = False
        if not in_ad_block:
            if ad_count == 1 or ad_count == 2:
                i = old_i
            ad_count = 0

        i += 1
    combined_transitions.append(transitions[-1])

    # Now classify segments based on the updated transitions
    segmented_video = []
    i = 0

    while i < len(combined_transitions) - 1:
        block_start = combined_transitions[i]
        block_end = combined_transitions[i + 1]
        block_duration = block_end - block_start

        if is_within_buffer(block_duration, buffer):
            # Assign 'ad' or 'program' based on the duration between new transitions
            if any(is_within_buffer(block_duration, ad_length) for ad_length in ad_lengths):
                segmented_video.append(('ad', block_start, block_duration))
            else:
                segmented_video.append(('program', block_start, block_duration))
        else:
            # If not within buffer, classify as 'program'
            segmented_video.append(('program', block_start, block_duration))

        i += 1

    i = 0
    while i < len(segmented_video) - 1:
        if segmented_video[i][0] == 'program':
            new_start = segmented_video[i][1]
            new_duration = segmented_video[i][2]
            j = i + 1

            # Merge consecutive program segments
            while j < len(segmented_video) and segmented_video[j][0] == 'program':
                new_duration += segmented_video[j][2]
                j += 1

            # Update the merged segment
            segmented_video[i] = ('program', new_start, new_duration)
            # Remove the merged segments
            del segmented_video[i + 1:j]
        # Increment i only once at the end of the loop
        i += 1

    return segmented_video
