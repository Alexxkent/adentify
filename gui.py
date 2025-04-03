from tkinter import filedialog
from multiprocessing import Process, Queue
import queue
import main
import datetime
import threading
import identify_logo
import os
import yaml
from tkinter import ttk
import tkinter as tk
import scripts
import signal
import logging


update_queue = Queue()
global process
global training_thread
file_directory = ""
xlsx_name = ""
output_directory = ""
model_output_directory = ""
robo_directory = ""
input_entry4 = None
input_entry5 = None
bg_colour = '#D3D3D3'
txt_colour = '#2E2E2E'


def browse_files(input_entry):
    # Use the global keyword to indicate that you are using the global variable
    global file_directory
    file_directory = filedialog.askopenfilename(
        initialdir="/",
        title="Select a File",
        filetypes=(("MKV files", "*.mkv"), ("MP4 files", "*.mp4"), ("all files", "*.*"))
    )
    input_entry.delete(0, tk.END)  # Clear the existing text in the Entry widget
    input_entry.insert(0, file_directory)  # Insert the selected file directory into the Entry widget


def browse_folders(input_entry):
    # Use the global keyword to indicate that you are using the global variable
    global output_directory
    output_directory = filedialog.askdirectory(initialdir = "/", title = "Select a Directory")
    input_entry.delete(0, tk.END)  # Clear the existing text in the Entry widget
    input_entry.insert(0, output_directory)  # Insert the selected directory into the Entry widget


def browse_folders_for_model(input_entry):
    # Use the global keyword to indicate that you are using the global variable
    global model_output_directory
    model_output_directory = filedialog.askdirectory(initialdir = "/", title = "Select a Directory")
    input_entry.delete(0, tk.END)  # Clear the existing text in the Entry widget
    input_entry.insert(0, model_output_directory)  # Insert the selected directory into the Entry widget


def browse_folders_for_robo(input_entry):
    # Use the global keyword to indicate that you are using the global variable
    global robo_directory
    robo_directory = filedialog.askdirectory(initialdir = "/", title = "Select a Directory")
    input_entry.delete(0, tk.END)  # Clear the existing text in the Entry widget
    input_entry.insert(0, robo_directory)  # Insert the selected directory into the Entry widget


def submit(window):
    global file_directory
    global output_directory
    global model_output_directory
    global input_entry4
    global input_entry5
    global process  # Declare the global process variable
    global update_queue

    valid_string = isinstance(input_entry4.get(), str) and input_entry4.get().strip() != ''
    channel = input_entry4.get().strip()
    date = input_entry5.get().strip()

    try:
        datetime.datetime.strptime(input_entry5.get(), '%Y-%m-%d')
        valid_date = True
    except ValueError:
        valid_date = False

    valid_file = file_directory.endswith(('.mkv', '.mp4'))

    valid_model_directory = (
        os.path.isdir(model_output_directory) and
        os.path.isdir(os.path.join(model_output_directory, "weights")) and
        os.path.isfile(os.path.join(model_output_directory, "weights", "best.pt"))
    )

    if valid_file and os.path.isdir(output_directory) and not os.path.isfile(output_directory) and valid_string and valid_date and valid_model_directory:
        # Start the loading screen in a separate daemon thread
        geometry = window.geometry()
        # Extract the x and y position from the geometry string
        _, x, y = geometry.split('+')
        window.destroy()
        loading_thread = threading.Thread(target=show_loading_screen, args=(x, y))
        # loading_thread.daemon = True
        loading_thread.start()
        # Start the identify_process in a separate process
        process = Process(target=main.identify_process, args=(file_directory, output_directory, model_output_directory, channel, date, update_queue))
        process.start()

        process.join()

        # Do not join the process here. It will run in the background.
    else:
        scripts.show_error("An entry is incorrect, please check your input")


def show_main_screen(x, y):
    global input_entry4, input_entry5

    window = tk.Tk()
    if x and y:
        window.geometry(f"+{x}+{y}")
    window.iconbitmap(scripts.resource_path("icon.ico"))

    window.config(bg=bg_colour)
    window.title("adentify")

    frame1 = tk.Frame(window, bg=bg_colour)  # Create a new frame for the first row
    frame1.pack(padx=20, pady=10)  # Add padding to the frame

    input_path1 = tk.Label(frame1, text="Input File Path:", bg=bg_colour, fg=txt_colour)
    input_path1.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame1 = tk.Frame(frame1, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame1.pack()
    input_entry1 = tk.Entry(entry_frame1, text="", width=40)
    input_entry1.pack(side=tk.LEFT, padx=10)
    button1 = tk.Button(entry_frame1, text="Browse Files", fg=txt_colour, command=lambda: browse_files(input_entry1))
    button1.pack(side=tk.LEFT, padx=10)

    frame2 = tk.Frame(window, bg=bg_colour)  # Create a new frame for the second row
    frame2.pack(padx=20, pady=10)  # Add padding to the frame

    input_path2 = tk.Label(frame2, text="Output File Path:", bg=bg_colour, fg=txt_colour)
    input_path2.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame2 = tk.Frame(frame2, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame2.pack()
    input_entry2 = tk.Entry(entry_frame2, text="", width=40)
    input_entry2.pack(side=tk.LEFT, padx=10)
    button2 = tk.Button(entry_frame2, text="Browse Files", fg=txt_colour, command=lambda: browse_folders(input_entry2))
    button2.pack(side=tk.LEFT, padx=10)

    frame3 = tk.Frame(window, bg=bg_colour)  # Create a new frame for the second row
    frame3.pack(padx=20, pady=10)  # Add padding to the frame

    input_path3 = tk.Label(frame3, text="Model File Path", bg=bg_colour, fg=txt_colour)
    input_path3.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame3 = tk.Frame(frame3, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame3.pack()
    input_entry3 = tk.Entry(entry_frame3, text="", width=40)
    input_entry3.pack(side=tk.LEFT, padx=10)
    button3 = tk.Button(entry_frame3, text="Browse Files", fg=txt_colour, command=lambda: browse_folders_for_model(input_entry3))
    button3.pack(side=tk.LEFT, padx=10)

    frame4 = tk.Frame(window, bg=bg_colour)  # Create a new frame for the second row
    frame4.pack(padx=20, pady=10, anchor='w')  # Add padding to the frame

    input_path4 = tk.Label(frame4, text="TV Channel of Video:", bg=bg_colour, fg=txt_colour)
    input_path4.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame4 = tk.Frame(frame4, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame4.pack()
    input_entry4 = tk.Entry(entry_frame4, text="", width=40)
    input_entry4.pack(side=tk.LEFT, padx=10)

    frame5 = tk.Frame(window, bg=bg_colour)  # Create a new frame for the second row
    frame5.pack(padx=20, pady=10, anchor='w')  # Add padding to the frame

    input_path5 = tk.Label(frame5, text="Date of Recording (YYYY-MM-DD):", bg=bg_colour, fg=txt_colour)
    input_path5.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame5 = tk.Frame(frame5, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame5.pack()
    input_entry5 = tk.Entry(entry_frame5, text="", width=40)
    input_entry5.pack(side=tk.LEFT, padx=10)

    submit_button = tk.Button(window, text="Submit", fg=txt_colour, command=lambda: submit(window))
    submit_button.pack(side=tk.LEFT, padx=30, pady=20)  # Add padding to the submit button

    train_button = tk.Button(window, text="Train", fg=txt_colour, command=lambda: go_to_train(window))
    train_button.pack(side=tk.LEFT, padx=30, pady=20)  # Add padding to the submit button

    window.resizable(False, False)
    window.mainloop()


def go_to_train(window):
    geometry = window.geometry()
    # Extract the x and y position from the geometry string
    _, x, y = geometry.split('+')
    window.destroy()
    show_train_screen(x, y)


def show_loading_screen(x, y):
    global bg_colour
    loading_window = tk.Tk()
    loading_window.geometry(f"+{x}+{y}")
    loading_window.iconbitmap(scripts.resource_path("icon.ico"))
    loading_window.title("adentify")
    loading_window.config(bg=bg_colour)
    loading_window.geometry("350x150")

    # Create a label to display loading text
    loading_label = tk.Label(loading_window, text=f"Generating scene list ({1}%)")
    loading_label.config(bg=bg_colour, fg=txt_colour, wraplength=280)
    loading_label.pack(pady=20)

    # Create a progress bar in determinate mode
    progress = ttk.Progressbar(loading_window, orient=tk.HORIZONTAL, length=200, mode='determinate')
    progress.pack(pady=10)

    def on_close():
        global process
        if process and process.is_alive():
            os.kill(process.pid, signal.SIGTERM)  # Terminate the process
        update_queue.put('kill')

    loading_window.protocol("WM_DELETE_WINDOW", on_close)
    loading_window.resizable(False, False)
    loading_window.after(1000, lambda: update_loading_screen(loading_window, loading_label, progress))
    # Start the Tkinter event loop
    loading_window.mainloop()


def show_train_screen(x, y):
    # Set the position of the new window based on the base window's position
    train_window = tk.Tk()
    train_window.geometry(f"+{x}+{y}")
    train_window.iconbitmap(scripts.resource_path("icon.ico"))

    train_window.config(bg=bg_colour)
    train_window.title("adentify")

    frame1 = tk.Frame(train_window, bg=bg_colour)  # Create a new frame for the first row
    frame1.pack(padx=20, pady=10)  # Add padding to the frame

    input1 = tk.Label(frame1, text="Roboflow Dataset Path:", bg=bg_colour, fg=txt_colour)
    input1.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame = tk.Frame(frame1, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame.pack()
    entry1 = tk.Entry(entry_frame, text="", width=40)
    entry1.pack(side=tk.LEFT, padx=10)
    button1 = tk.Button(entry_frame, text="Browse Files", command=lambda: browse_folders_for_robo(entry1))
    button1.pack(side=tk.LEFT, padx=10)

    frame2 = tk.Frame(train_window, bg=bg_colour)  # Create a new frame for the first row
    frame2.pack(padx=20, pady=10)  # Add padding to the frame

    input2 = tk.Label(frame2, text="Dataset File Path:", bg=bg_colour, fg=txt_colour)
    input2.pack(anchor='w', padx=10)  # Anchor to the west (left)
    entry_frame2 = tk.Frame(frame2, bg=bg_colour)  # Create a new frame for the entry and button
    entry_frame2.pack()
    entry2 = tk.Entry(entry_frame2, text="", width=40)
    entry2.pack(side=tk.LEFT, padx=10)
    button2 = tk.Button(entry_frame2, text="Browse Files", fg=txt_colour, command=lambda: browse_folders(entry2))
    button2.pack(side=tk.LEFT, padx=10)

    train_button = tk.Button(train_window, text="Submit", fg=txt_colour, command=lambda: train(train_window))
    train_button.pack(side=tk.LEFT, padx=30, pady=20)  # Add padding to the submit button

    return_button = tk.Button(train_window, text="Return", fg=txt_colour, command=lambda: go_to_main(train_window))
    return_button.pack(side=tk.LEFT, padx=30, pady=20)  # Add padding to the submit button

    train_window.resizable(False, False)
    train_window.mainloop()


def go_to_main(window):
    geometry = window.geometry()
    # Extract the x and y position from the geometry string
    _, x, y = geometry.split('+')
    window.destroy()
    show_main_screen(x, y)


def train(window):
    global output_directory
    global robo_directory

    # Define the path to the YAML file
    yaml_path = os.path.join(robo_directory, 'data.yaml')

    # Load the YAML file
    with open(yaml_path, 'r') as file:
        data = yaml.safe_load(file)

    # Check if the class names follow the required pattern
    valid = all(name.startswith(('a-', 'g-', 'f-')) for name in data['names'])

    # Directories to check for corrupted images
    directories_to_check = [f'{robo_directory}/train/images/', f'{robo_directory}/test/images/', f'{robo_directory}/valid/images/']

    # Check for corrupted images
    if valid:
        valid = scripts.check_corrupted_images(directories_to_check)
    else:
        scripts.show_error("Improper company naming")
    if valid:
        robo_dir = robo_directory
        data_dir = output_directory
        geometry = window.geometry()
        # Extract the x and y position from the geometry string
        _, x, y = geometry.split('+')
        window.destroy()
        show_console_window(x, y, data_dir, robo_dir)


class TkinterLogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        try:
            message = self.format(record)
            self.text_widget.insert(tk.END, message + '\n')
            self.text_widget.yview(tk.END)  # Scroll to the end
        except Exception:
            self.handleError(record)


def show_console_window(x, y, data_dir, robo_dir):
    """
    Function to create and show the Tkinter console window.
    """
    global bg_colour
    # Create the main Tkinter window
    root = tk.Tk()
    root.iconbitmap(scripts.resource_path("icon.ico"))
    root.geometry(f"+{x}+{y}")
    root.config(bg=bg_colour)
    root.title("training console")

    # Create a Text widget to display the console output
    console = tk.Text(root, wrap=tk.WORD, height=20, width=80)
    console.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    log_handler = TkinterLogHandler(console)
    log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    start_training(data_dir, robo_dir, log_handler)
    # Start the Tkinter event loop

    def on_close():
        global training_thread
        if training_thread.is_alive():
            os.kill(os.getpid(), signal.SIGTERM)  # Terminate the process
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def start_training(data_dir, robo_dir, log_handler):
    # Start the training process in a separate thread
    global training_thread
    training_thread = threading.Thread(target=identify_logo.fine_tune_yolo, args=(data_dir, robo_dir, log_handler))
    training_thread.start()


def update_loading_screen(loading_window, loading_label, progress):
    global update_queue
    global output_directory
    global xlsx_name

    try:
        process_num = update_queue.get_nowait()
    except queue.Empty:
        process_num = None

    if process_num:
        if process_num == 'process1':
            update_progress(loading_window, loading_label, progress, start=1, end=50, step=1,
                            label_text='Generating audio silence list')
        elif process_num == 'process2':
            loading_label.config(text=f'Finding transitions (50%)')
            progress['value'] = 50
        elif process_num == 'process3':
            update_progress(loading_window, loading_label, progress, start=51, end=75, step=1,
                            label_text='Identifying ads')
        elif process_num == 'process4':
            update_progress(loading_window, loading_label, progress, start=76, end=100, step=1,
                            label_text='Identifying ads')
            # Reset to 0% as part of the process
            loading_label.config(text=f'Detecting brands (0%)')
            progress['value'] = 0
        elif isinstance(process_num, int):
            loading_label.config(text=f'Detecting brands ({process_num}%)')
            progress['value'] = process_num
        elif process_num == 'process5':
            loading_label.config(text=f'Complete! Generating excel file (100%)')
            progress['value'] = 100
        elif process_num.startswith('process6-'):
            xlsx_name = process_num.split('-')[1]
            loading_label.config(text=f'Results saved to {output_directory}/adentify-results/{xlsx_name}')
            progress.pack_forget()
            button = tk.Button(loading_window, text="Launch Results", fg=txt_colour, command=on_button_click)
            button.pack(pady=10)
        elif process_num == 'kill':
            loading_window.destroy()

    # Schedule the next update
    loading_window.after(100, lambda: update_loading_screen(loading_window, loading_label, progress))


def on_button_click():
    global xlsx_name
    os.startfile(f'{output_directory}/adentify-results/{xlsx_name}')


def update_progress(window, label, progress, start, end, step, label_text):
    # Internal function to handle progress updates
    def update():
        nonlocal start
        if start <= end:
            label.config(text=f'{label_text} ({start}%)')
            progress['value'] = start
            start += step
            window.after(100, update)  # Schedule the next update
        else:
            label.config(text=f'{label_text} ({end}%)')
            progress['value'] = end

    update()
