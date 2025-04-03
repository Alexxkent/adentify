from ultralytics import YOLO
import os
import parse_video
import torch
import segment_video
import sys
import logging
import scripts


# Custom stream handler to redirect stdout to logger
class LoggerStreamHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        try:
            message = self.format(record)
            self.text_widget.insert('end', message + '\n')
            self.text_widget.yview('end')
        except Exception:
            self.handleError(record)


def train_yolo(data_path, log_handler):
    # Redirect stdout to logging
    class StreamToLogger(object):
        def __init__(self, logger, level=logging.INFO):
            self.logger = logger
            self.level = level

        def write(self, buf):
            if buf:
                self.logger.log(self.level, buf.strip())

        def flush(self):
            pass

    # Initialize logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)

    # Redirect stdout
    sys.stdout = StreamToLogger(logger)
    sys.stderr = sys.stdout

    # Load the model
    model = YOLO(scripts.resource_path("yolov8l.pt"))

    # Train the model
    model.train(
        data=data_path,
        epochs=20,
        imgsz=640,
        batch=4,
        device=0,
        optimizer="Adam",
        lr0=1e-3,
        augment=True,
        weight_decay=1e-4,
        verbose=True
    )


def fine_tune_yolo(data_dir, robo_dir, log_handler):

    new_dir = scripts.create_dataset_directory(os.path.dirname(data_dir))

    scripts.move_files(f'{robo_dir}/train/labels/', f'{new_dir}/labels/train')
    scripts.move_files(f'{robo_dir}/train/images/', f'{new_dir}/images/train')
    scripts.move_files(f'{robo_dir}/valid/labels/', f'{new_dir}/labels/val')
    scripts.move_files(f'{robo_dir}/valid/images/', f'{new_dir}/images/val')
    scripts.move_files(f'{robo_dir}/test/labels/', f'{new_dir}/labels/test')
    scripts.move_files(f'{robo_dir}/test/images/', f'{new_dir}/images/test')
    scripts.combine_datasets(robo_dir, data_dir, new_dir)
    train_yolo(new_dir + '/data.yaml', log_handler)


def get_logos(segmented_video, video_path, model_output_path, update_queue):
    scripts.delete_jpg_files(scripts.resource_path("images"))

    final_block_list = list()
    inc = 1  # 1 frame per second

    for block in segmented_video:

        if block[0] == 'ad':
            start = block[1]
            end = block[1] + block[2]
        else:
            final_block_list.append((block[0], block[1], block[2], 'no ad detected'))
            continue

        time = start

        brands = list()

        while time < end - inc:
            try:
                frame = parse_video.get_frame_at_timestamp(time, video_path)
                brand = list(get_brands_in_frame(frame, model_output_path, time, update_queue))
                if brand:
                    for br in brand:
                        if br[len(br)-1] == 1:
                            br = br[:-1]
                        brands.append((br, time))

                time += inc
            except Exception as e:
                scripts.show_error(f"An error occurred: {e}")
                break

        brand_to_add = 'no ad detected'
        count_dict = dict()
        for brand in brands:
            company_name = brand[0]  # Extract the company name from the tuple
            if company_name not in count_dict:
                count_dict[company_name] = 1  # Set the count to 1 when you first encounter a company name
            else:
                count_dict[company_name] += 1  # If the company name is already in the dictionary, increment the count

        if block[2] < 16:
            highest_count = 0
            for brand, count in count_dict.items():
                if count > highest_count:
                    highest_count = count
                    brand_to_add = brand
        elif 29 < block[2] < 31:
            if len(count_dict) == 1:
                keys = list(count_dict.keys())
                brand_to_add = keys[0]
            elif len(count_dict) > 1:
                brands_in_blocks = ['no ad detected', 'no ad detected']
                for i in range(2):
                    brand_to_add = 'no ad detected'  # Reset brand_to_add
                    count_per_block = dict()
                    start_time = block[1] + i * (block[2] / 2)
                    end_time = start_time + (block[2] / 2)
                    for brand in brands:
                        if start_time <= brand[1] < end_time:
                            company_name = brand[0]
                            if company_name not in count_per_block:
                                count_per_block[company_name] = 1
                            else:
                                count_per_block[company_name] += 1
                    if count_per_block:
                        brand_to_add = max(count_per_block, key=count_per_block.get)
                    brands_in_blocks[i] = brand_to_add
                for i in range(1, 2):
                    if brands_in_blocks[i] == 'no ad detected':
                        brands_in_blocks[i] = brands_in_blocks[i - 1]
                temp_block_list = []
                start_time = block[1]
                last_block_length = 0
                current_brand = brands_in_blocks[0]
                for i in range(2):
                    if brands_in_blocks[i] != current_brand:
                        block_duration = i * (block[2] / 2) - last_block_length
                        temp_block_list.append((block[0], start_time, block_duration, current_brand))
                        start_time += block_duration
                        current_brand = brands_in_blocks[i]
                        last_block_length += block_duration
                block_duration = block[2] - last_block_length
                temp_block_list.append((block[0], start_time, block_duration, current_brand))
                final_block_list.extend(temp_block_list)
                continue
        else:
            if len(count_dict) == 1:
                keys = list(count_dict.keys())
                brand_to_add = keys[0]
            elif len(count_dict) > 1:
                brands_in_blocks = ['no ad detected', 'no ad detected', 'no ad detected', 'no ad detected']
                for i in range(4):
                    brand_to_add = 'no ad detected'  # Reset brand_to_add
                    count_per_block = dict()
                    start_time = block[1] + i * (block[2] / 4)
                    end_time = start_time + (block[2] / 4)
                    for brand in brands:
                        if start_time <= brand[1] < end_time:
                            company_name = brand[0]
                            if company_name not in count_per_block:
                                count_per_block[company_name] = 1
                            else:
                                count_per_block[company_name] += 1
                    if count_per_block:
                        brand_to_add = max(count_per_block, key=count_per_block.get)
                    brands_in_blocks[i] = brand_to_add
                # New logic to update all blocks in between two blocks with the same company name
                for i in range(3, 0, -1):
                    if brands_in_blocks[i] in brands_in_blocks[:i]:
                        for j in range(i - 1, -1, -1):
                            if brands_in_blocks[j] == 'no ad detected':
                                brands_in_blocks[j] = brands_in_blocks[i]

                for i in range(1, 4):
                    if brands_in_blocks[i] in brands_in_blocks[:i]:
                        brands_in_blocks[i] = brands_in_blocks[i - 1]
                for i in range(1, 4):
                    if brands_in_blocks[i] == 'no ad detected':
                        brands_in_blocks[i] = brands_in_blocks[i - 1]

                temp_block_list = []
                start_time = block[1]
                last_block_length = 0
                current_brand = brands_in_blocks[0]
                for i in range(4):
                    if brands_in_blocks[i] != current_brand:
                        block_duration = i * (block[2] / 4) - last_block_length
                        temp_block_list.append((block[0], start_time, block_duration, current_brand))
                        start_time += block_duration
                        current_brand = brands_in_blocks[i]
                        last_block_length += block_duration
                block_duration = block[2] - last_block_length
                temp_block_list.append((block[0], start_time, block_duration, current_brand))
                final_block_list.extend(temp_block_list)
                continue

        final_block_list.append((block[0], block[1], block[2], brand_to_add))

    update_queue.put('process5')
    return final_block_list


def get_brands_in_frame(frame, model_output_path, file_name, update_queue):

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Construct the model path using the specified model_output_path
    model_path = os.path.join(model_output_path, "weights", "best.pt")
    if not os.path.exists(model_path):
        raise ValueError(f"No model found at {model_path}")

    model = YOLO(model_path).to(device)

    # Perform prediction on the frame using the specified device
    results = model.predict(frame, conf=0.85, device=device)

    # Extract classes detected in the frame
    detected_classes = set()
    clist = results[0].boxes.cls
    for cno in clist:
        detected_classes.add(model.names[int(cno)].split('_')[0])

    # Save the annotated frame
    if detected_classes:
        # Get the directory of the executable or script
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")

        save_path = os.path.join(base_path, f"images/{file_name}.jpg")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        results[0].save(filename=save_path)

    update_queue.put(int((file_name/segment_video.vid_len)*100))

    return detected_classes
