import sys
import os
import tkinter as tk
from tkinter import messagebox
import shutil
import yaml
import pandas as pd
from datetime import timedelta
from PIL import Image, UnidentifiedImageError


def show_error(message):
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    messagebox.showerror("Error", message)
    root.destroy()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def move_files(source_directory: str, destination_directory: str):

    # Create the destination directory if it doesn't exist
    os.makedirs(destination_directory, exist_ok=True)

    # Move all files from the source to the destination directory
    for file_name in os.listdir(source_directory):
        source = os.path.join(source_directory, file_name)
        destination = os.path.join(destination_directory, file_name)
        shutil.move(source, destination)


def delete_jpg_files(directory):
    if not os.path.exists(directory):
        # Create the images directory if it does not exist
        os.makedirs(directory)
        return

    files = os.listdir(directory)
    if not files:
        return

    for file in files:
        if file.endswith('.jpg'):
            file_path = os.path.join(directory, file)
            try:
                os.remove(file_path)
            except Exception as e:
                pass


def create_dataset_directory(base_path):
    # Find the next available dataset number
    existing_datasets = [d for d in os.listdir(base_path) if d.startswith('dataset')]
    nums = [int(d[len('dataset'):]) for d in existing_datasets if d[len('dataset'):].isdigit()]
    next_num = max(nums, default=0) + 1
    new_dataset_dir = os.path.join(base_path, f'dataset{next_num}')

    # Create the main dataset directory
    os.makedirs(new_dataset_dir, exist_ok=True)

    # Create images and labels directories with their subdirectories
    for main_folder in ['images', 'labels']:
        for sub_folder in ['test', 'train', 'val']:
            os.makedirs(os.path.join(new_dataset_dir, main_folder, sub_folder), exist_ok=True)

    return new_dataset_dir


def combine_datasets(dataset1_path: str, dataset2_path: str, new_dataset_path: str):

    # Create the new directory if it doesn't exist
    os.makedirs(new_dataset_path, exist_ok=True)

    # Load the YAML files from the two datasets
    def load_yaml(file_path):
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)

    dataset1_yaml = load_yaml(os.path.join(dataset1_path, 'data.yaml'))
    dataset2_yaml = load_yaml(os.path.join(dataset2_path, 'data.yaml'))

    # Combine the YAML data and adjust the class numbering
    combined_names = dataset1_yaml['names'] + [name for name in dataset2_yaml['names'] if name not in dataset1_yaml['names']]
    combined_yaml = {
        'nc': len(combined_names),
        'names': combined_names,
        'test': os.path.join(new_dataset_path, 'images/test'),
        'train': os.path.join(new_dataset_path, 'images/train'),
        'val': os.path.join(new_dataset_path, 'images/val'),
    }

    # Write the combined YAML data to a new file in the new directory
    with open(os.path.join(new_dataset_path, 'data.yaml'), 'w') as file:
        file.write(f"nc: {combined_yaml['nc']}\n")
        file.write(f"names: {combined_yaml['names']}\n")
        file.write(f"test: {combined_yaml['test']}\n")
        file.write(f"train: {combined_yaml['train']}\n")
        file.write(f"val: {combined_yaml['val']}\n")

    # Copy all files from the two datasets into the new directory and update class numbers in label files
    for dataset_path, yaml_data in zip([dataset1_path, dataset2_path], [dataset1_yaml, dataset2_yaml]):
        for split in ['train', 'test', 'val']:
            for root, dirs, files in os.walk(os.path.join(dataset_path, 'labels', split)):
                for file in files:
                    source = os.path.join(root, file)
                    destination_dir = os.path.join(new_dataset_path, 'labels', split)
                    os.makedirs(destination_dir, exist_ok=True)
                    destination = os.path.join(destination_dir, file)

                    # Update class numbers in label file
                    with open(source, 'r') as f:
                        lines = f.readlines()
                    with open(destination, 'w') as f:
                        for line in lines:
                            parts = line.split()
                            class_number = int(parts[0])
                            new_class_number = combined_yaml['names'].index(yaml_data['names'][class_number])
                            f.write(' '.join([str(new_class_number)] + parts[1:]) + '\n')

            # Copy the image files
            for root, dirs, files in os.walk(os.path.join(dataset_path, 'images', split)):
                for file in files:
                    source = os.path.join(root, file)
                    destination_dir = os.path.join(new_dataset_path, 'images', split)
                    os.makedirs(destination_dir, exist_ok=True)
                    destination = os.path.join(destination_dir, file)
                    shutil.copy(source, destination)


def generate_results(blocks, output_path, channel, date):
    # Define the folder name
    folder_name = "adentify-results"

    # Check if output_path already ends with "adentify-results"
    if output_path.endswith(folder_name):
        folder_path = output_path
    else:
        # Create the full path to the folder
        folder_path = os.path.join(output_path, folder_name)

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Initialize the file number
    num = 1

    # Define the file name
    xlsx_name = f"results_{num}.xlsx"  # Change the extension to .xlsx

    # Check if the file already exists
    while os.path.exists(os.path.join(folder_path, xlsx_name)):
        # If the file exists, increment the number and update the file name
        num += 1
        xlsx_name = f"results_{num}.xlsx"  # Change the extension to .xlsx

    df = pd.DataFrame(columns=['Ad number', 'Chanel', 'Date of recording', 'Time of recording', 'Duration of recording','Type of ad', 'Type of product', 'Brand name'])
    ad_num = 1
    for i, block in enumerate(blocks):
        if block[0] == 'ad':
            ad_number = ad_num  # Assuming ad number starts from 1 and increments by 1 for each block
            time_of_recording = str(timedelta(seconds=block[1]))
            duration_of_recording = str(timedelta(seconds=block[2]))
            date_of_recording = date
            type_of_ad = "Commercial"
            product_char = block[3][0]
            if product_char == 'a':
                type_of_product = 'alcohol'
            elif product_char == 'f':
                type_of_product = 'food'
            elif product_char == 'g':
                type_of_product = 'gambling'
            else:
                type_of_product = "other"

            original_string = block[3]
            if block[3] == 'no ad detected':
                brand_name = 'n/a'
            else:
                pos = original_string.find("-")

                if pos != -1:
                    brand_name = original_string[pos + 1:]
                else:
                    brand_name = ""

            df.loc[i] = [ad_number, channel, date_of_recording, time_of_recording, duration_of_recording, type_of_ad, type_of_product, brand_name]
            ad_num += 1
    # Create the Excel file
    df.to_excel(os.path.join(folder_path, xlsx_name), index=False)  # Use to_excel instead of to_csv
    return xlsx_name


def check_corrupted_images(directories):
    corrupted_files = []

    for directory in directories:
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)

            # Check if the file is an image and if it is corrupted
            try:
                with Image.open(file_path) as img:
                    img.verify()  # Verify the image file is not corrupted
            except (IOError, UnidentifiedImageError):
                corrupted_files.append(file_path)

    # If there are any corrupted files, return False and show an error message
    if corrupted_files:
        corrupted_files_list = "\n".join(corrupted_files)
        error_message = f"The following files are corrupted:\n{corrupted_files_list}"
        show_error(error_message)
        return False
    return True
