import cv2
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading

# PySceneDetect imports - updated to use open_video
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector


class VideoUtilityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Utilities")
        self.geometry("600x800") # Increased window height for the new button
        self.configure(bg="#2c3e50") # Dark background
        
        # Video playback properties
        self.cap = None
        self.is_playing = False
        self.after_id = None # To manage the after() loop
        self.last_frame = None # To store the last frame for resizing events
        self.video_delay = 25 # Default delay in ms for video playback
        
        # UI elements
        self.output_filename = tk.StringVar(value="last_frame.png")

        # Clip editor properties
        self.clip_list = []

        self.setup_ui()

    def setup_ui(self):
        """Sets up the UI for the entire application using a grid layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) # Video frame
        self.rowconfigure(1, weight=0) # Clip listbox
        self.rowconfigure(2, weight=0) # Clip buttons
        self.rowconfigure(3, weight=0) # Filename entry
        self.rowconfigure(4, weight=0) # Action buttons
        
        # Video display area
        video_frame = tk.Frame(self, bg="black")
        video_frame.grid(row=0, column=0, pady=(10, 20), padx=10, sticky="nsew")
        video_frame.grid_propagate(False) 
        
        self.video_label = tk.Label(video_frame, bg="black")
        self.video_label.grid(row=0, column=0, sticky="nsew")
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        self.video_label.bind("<Configure>", self.on_label_resize)

        # Clip list and control buttons
        listbox_frame = tk.Frame(self, bg="#2c3e50")
        listbox_frame.grid(row=1, column=0, pady=(10, 5), padx=10, sticky="nsew")
        listbox_frame.columnconfigure(0, weight=1, minsize=400)
        listbox_frame.columnconfigure(1, weight=1, minsize=150)
        
        tk.Label(listbox_frame, text="Selected Clips:", bg="#2c3e50", fg="#ecf0f1", font=("Arial", 12, "bold")).grid(row=0, column=0, pady=(0, 5), sticky="w")
        
        self.clip_listbox = tk.Listbox(listbox_frame, bg="#34495e", fg="#ecf0f1", selectbackground="#3498db", relief=tk.FLAT, height=5)
        self.clip_listbox.grid(row=1, column=0, sticky="nsew")
        self.clip_listbox.bind("<<ListboxSelect>>", self.on_clip_select)

        # Video preview label in the clips section
        preview_container = tk.Frame(listbox_frame, bg="black")
        preview_container.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        preview_container.grid_propagate(False)

        self.preview_label = tk.Label(preview_container, bg="black")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        preview_container.rowconfigure(0, weight=1)
        preview_container.columnconfigure(0, weight=1)
        self.preview_label.bind("<Configure>", self.on_label_resize)
        
        # Clip control buttons frame
        clip_buttons_frame = tk.Frame(self, bg="#2c3e50")
        clip_buttons_frame.grid(row=2, column=0, pady=10, padx=10, sticky="ew")
        for i in range(4):
            clip_buttons_frame.columnconfigure(i, weight=1)

        tk.Button(clip_buttons_frame, text="Add Clip", command=self.add_clip, bg="#27ae60", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(clip_buttons_frame, text="Remove Clip", command=self.remove_clip, bg="#e74c3c", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(clip_buttons_frame, text="Move Up", command=self.move_up, bg="#3498db", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, sticky="ew")
        tk.Button(clip_buttons_frame, text="Move Down", command=self.move_down, bg="#3498db", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5, sticky="ew")
        
        # Output filename entry and action buttons
        output_frame = tk.Frame(self, bg="#2c3e50")
        output_frame.grid(row=3, column=0, pady=(10, 0), padx=10, sticky="ew")
        output_frame.columnconfigure(1, weight=1)

        tk.Label(output_frame, text="Output File Name:", bg="#2c3e50", fg="#ecf0f1", font=("Arial", 12, "bold")).grid(row=0, column=0, pady=(0, 5), sticky="w")
        tk.Entry(output_frame, textvariable=self.output_filename, relief=tk.FLAT).grid(row=0, column=1, padx=(5, 0), ipady=3, sticky="ew")

        action_buttons_frame = tk.Frame(self, bg="#2c3e50")
        action_buttons_frame.grid(row=4, column=0, pady=20, padx=10, sticky="ew")
        action_buttons_frame.columnconfigure(0, weight=1)
        action_buttons_frame.columnconfigure(1, weight=1)
        action_buttons_frame.columnconfigure(2, weight=1)

        tk.Button(action_buttons_frame, text="Extract Last Frame", command=self.extract_frame, bg="#e74c3c", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 12, "bold")).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(action_buttons_frame, text="Merge Clips", command=self.merge_clips, bg="#27ae60", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 12, "bold")).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(action_buttons_frame, text="Reverse Clip", command=self.reverse_clip, bg="#3498db", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 12, "bold")).grid(row=0, column=2, padx=5, sticky="ew")
        
        tk.Button(action_buttons_frame, text="✨ AI Auto Clip ✨", command=self.ai_auto_clip, bg="#9b59b6", fg="#ecf0f1", relief=tk.FLAT, font=("Arial", 12, "bold")).grid(row=1, column=0, columnspan=3, pady=(10,0), padx=5, sticky="ew")

    def stop_video(self):
        """Stops the current video playback and clears both video labels."""
        self.is_playing = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.video_label:
            self.video_label.config(image=None)
            self.video_label.image = None
        if self.preview_label:
            self.preview_label.config(image=None)
            self.preview_label.image = None

    def on_clip_select(self, event):
        """Plays the selected video clip automatically when selected in the listbox."""
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            return

        file_path = self.clip_list[selected_indices[0]]
        self.play_video(file_path)

    def play_video(self, video_file):
        """Plays the video file in the GUI."""
        self.stop_video()
        
        if not os.path.exists(video_file):
            messagebox.showerror("Error", f"The file '{video_file}' was not found.")
            return

        self.cap = cv2.VideoCapture(video_file)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open the video file for playback.")
            return
        
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_delay = int(1000 / fps) if fps > 0 else 25

        self.is_playing = True
        self.update_frame()

    def on_label_resize(self, event):
        """
        Resizes and displays the last known video frame whenever the label's
        size changes (e.g., when the window is resized).
        """
        label = event.widget
        label_width = label.winfo_width()
        label_height = label.winfo_height()

        last_width = getattr(label, "_last_width", 0)
        last_height = getattr(label, "_last_height", 0)

        if abs(label_width - last_width) < 5 and abs(label_height - last_height) < 5:
            return
            
        label._last_width = label_width
        label._last_height = label_height
        
        if self.last_frame is not None:
            self._display_frame(self.last_frame, event.widget)
            
    def _display_frame(self, frame, label):
        """Helper function to resize and display a frame on a given label."""
        label_width = label.winfo_width()
        label_height = label.winfo_height()

        if label_width > 1 and label_height > 1:
            h, w, _ = frame.shape
            aspect_ratio = w / h
            new_w = label_width
            new_h = int(new_w / aspect_ratio)
            
            if new_h > label_height:
                new_h = label_height
                new_w = int(new_h * aspect_ratio)

            resized_frame = cv2.resize(frame, (new_w, new_h))
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            photo_image = ImageTk.PhotoImage(image)
            
            label.config(image=photo_image)
            label.image = photo_image

    def update_frame(self):
        """
        Reads a new frame from the video, stores it, and displays it on
        the video and preview labels.
        """
        if not self.is_playing or not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if ret:
            self.last_frame = frame
            self._display_frame(self.last_frame, self.video_label)
            self._display_frame(self.last_frame, self.preview_label)
            
            self.after_id = self.after(self.video_delay, self.update_frame)
        else:
            self.stop_video()
            
    def extract_frame(self):
        """Extracts the last frame of the selected video."""
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "Please select a clip to extract the last frame from.")
            return

        video_file = self.clip_list[selected_indices[0]]
        output_file = self.output_filename.get()

        if not os.path.exists(video_file):
            messagebox.showerror("Error", f"The file '{video_file}' was not found.")
            return

        output_dir = "last_frame"
        os.makedirs(output_dir, exist_ok=True)

        video_capture = cv2.VideoCapture(video_file)
        if not video_capture.isOpened():
            messagebox.showerror("Error", "Could not open the video file.")
            return

        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            messagebox.showerror("Error", "Could not determine the number of frames.")
            video_capture.release()
            return

        video_capture.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        success, last_frame = video_capture.read()

        if success:
            try:
                base_name, extension = os.path.splitext(output_file)
                base_name = re.sub(r'_\d+$', '', base_name)
                
                max_num = 0
                for filename in os.listdir(output_dir):
                    if filename.startswith(base_name) and filename.endswith(extension):
                        try:
                            num = int(re.search(r'_(\d+)', filename).group(1))
                            max_num = max(max_num, num)
                        except (AttributeError, ValueError):
                            pass
                
                next_num = max_num + 1
                new_filename = f"{base_name}_{next_num}{extension}"
                full_path = os.path.join(output_dir, new_filename)
                
                cv2.imwrite(full_path, last_frame)
                messagebox.showinfo("Success", f"The last frame has been saved as '{full_path}'.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save the image: {e}")
        else:
            messagebox.showerror("Error", "Could not read the last frame from the video.")

        video_capture.release()

    def reverse_clip(self):
        """Initiates the process of reversing the selected video clip."""
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Error", "Please select a clip to reverse.")
            return

        video_file = self.clip_list[selected_indices[0]]

        if not os.path.exists(video_file):
            messagebox.showerror("Error", f"The file '{video_file}' was not found.")
            return

        base_name, extension = os.path.splitext(os.path.basename(video_file))
        output_dir = "reversed_clip"
        os.makedirs(output_dir, exist_ok=True)

        counter = 1
        output_file_name = f"{base_name}_reversed{extension}"
        output_path = os.path.join(output_dir, output_file_name)

        while os.path.exists(output_path):
            output_file_name = f"{base_name}_reversed_{counter}{extension}"
            output_path = os.path.join(output_dir, output_file_name)
            counter += 1

        threading.Thread(target=self._run_reverse_clip, args=(video_file, output_path)).start()

    def _run_reverse_clip(self, video_file, output_file_path):
        """Internal function to handle the reversing process in a separate thread."""
        try:
            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                messagebox.showerror("Error", "Could not open the video file for reversing.")
                return

            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)

            cap.release()
            frames.reverse()

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file_path, fourcc, fps, (frame_width, frame_height))

            if not out.isOpened():
                messagebox.showerror("Error", "Could not create the output video file. Check codec compatibility.")
                return

            for frame in frames:
                out.write(frame)

            out.release()
            messagebox.showinfo("Success", f"Clip successfully reversed and saved to '{output_file_path}'.")

        except Exception as e:
            messagebox.showerror("Reversing Error", f"An error occurred during reversing: {e}")

    def ai_auto_clip(self):
        """
        Analyzes the selected video for scene changes and allows the user
        to select scenes to save as individual clips.
        """
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("AI Auto Clip", "Please select a clip from the list before using the AI Auto Clip feature.")
            return

        video_file = self.clip_list[selected_indices[0]]

        # Run scene detection in a separate thread to avoid freezing the GUI
        threading.Thread(target=self._run_scene_detection, args=(video_file,)).start()

    def _run_scene_detection(self, video_file):
        """Internal function to handle scene detection."""
        try:
            # Use the new open_video function, which is the modern replacement for the deprecated VideoManager.
            video = open_video(video_file)
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector())

            # The detect_scenes function now takes the video object directly.
            scene_manager.detect_scenes(video=video)
            scene_list = scene_manager.get_scene_list()

            if not scene_list:
                self.after(0, lambda: messagebox.showinfo("AI Auto Clip", "No significant scene changes were detected."))
                return

            # Present the detected scenes to the user in the main thread.
            self.after(0, self._show_scene_selection, video_file, scene_list)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("AI Auto Clip Error", f"An error occurred during scene detection: {e}"))


    def _show_scene_selection(self, video_file, scene_list):
        """
        Creates a new window to display the list of scenes.
        Automatically selects all clips and initiates the compilation.
        """
        selection_window = tk.Toplevel(self)
        selection_window.title("Compiling Clips...")
        selection_window.geometry("500x150")
        selection_window.configure(bg="#2c3e50")
        
        tk.Label(selection_window, text="Automatically compiling clips. Please wait...", bg="#2c3e50", fg="#ecf0f1", font=("Arial", 14, "bold")).pack(expand=True)

        selected_indices = list(range(len(scene_list)))
        output_dir = "compiled_clips"
        os.makedirs(output_dir, exist_ok=True)
        threading.Thread(target=self._compile_selected_clips_thread, args=(video_file, scene_list, selected_indices, output_dir, selection_window)).start()

    def _save_selected_clips_thread(self, video_file, scene_list, selected_indices, output_dir, window_to_close):
        """Saves selected clips in a background thread using OpenCV."""
        try:
            for index in selected_indices:
                start_timecode, end_timecode = scene_list[index]
                start_frame = start_timecode.get_frames()
                end_frame = end_timecode.get_frames()
                
                self._save_clip(video_file, start_frame, end_frame, output_dir, f"scene_{index + 1}")
            
            self.after(0, lambda: messagebox.showinfo("Success", f"Selected clips have been saved to the '{output_dir}' folder."))
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Save Error", f"Failed to save clips: {e}"))
        finally:
            self.after(0, window_to_close.destroy)

    def _save_clip(self, input_path, start_frame, end_frame, output_dir, clip_name):
        """Saves a clip from the video using OpenCV."""
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        output_filename = f"{clip_name}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Codec for MP4
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        if not out.isOpened():
            cap.release()
            raise IOError(f"Could not create output video file: {output_path}")

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for _ in range(int(end_frame - start_frame)):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        
        cap.release()
        out.release()
        
    def _compile_selected_clips_thread(self, video_file, scene_list, selected_indices, output_dir, window_to_close):
        """
        Compiles selected clips into a single video file in a background thread using OpenCV.
        """
        try:
            # Check if video file exists
            if not os.path.exists(video_file):
                self.after(0, lambda: messagebox.showerror("Error", f"Video file not found: {video_file}"))
                return

            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                self.after(0, lambda: messagebox.showerror("Error", "Could not open the video file for compilation."))
                return

            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Define the output file path with a counter to prevent overwriting
            base_name = os.path.basename(os.path.splitext(video_file)[0])
            counter = 1
            output_filename = f"{base_name}_compiled.mp4"
            output_path = os.path.join(output_dir, output_filename)
            while os.path.exists(output_path):
                output_filename = f"{base_name}_compiled_{counter}.mp4"
                output_path = os.path.join(output_dir, output_filename)
                counter += 1

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

            if not out.isOpened():
                cap.release()
                self.after(0, lambda: messagebox.showerror("Error", "Could not create the output video file. Check codec compatibility."))
                return
            
            # Iterate through the selected scene indices and write frames to the output file
            for index in selected_indices:
                start_frame = scene_list[index][0].get_frames()
                end_frame = scene_list[index][1].get_frames()

                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                
                for _ in range(int(end_frame - start_frame)):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
            
            # Release resources
            cap.release()
            out.release()
                
            self.after(0, lambda: messagebox.showinfo("Success", f"Selected scenes have been compiled into '{output_path}'."))
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Compilation Error", f"An error occurred during compilation: {e}"))
        finally:
            self.after(0, window_to_close.destroy)

    def add_clip(self):
        """Adds a video clip to the list for merging."""
        file_path = filedialog.askopenfilename(
            title="Select a video clip to add",
            filetypes=(("Video files", "*.mp4;*.avi;*.mov;*.mkv"), ("All files", "*.*"))
        )
        if file_path and file_path not in self.clip_list:
            self.clip_list.append(file_path)
            self.clip_listbox.insert(tk.END, os.path.basename(file_path))
            
            self.clip_listbox.selection_clear(0, tk.END)
            self.clip_listbox.selection_set(tk.END)
            self.clip_listbox.see(tk.END)

            self.play_video(file_path)

    def remove_clip(self):
        """Removes the selected video clip from the list."""
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            return
        
        index_to_remove = selected_indices[0]
        self.clip_listbox.delete(index_to_remove)
        self.clip_list.pop(index_to_remove)

    def move_up(self):
        """Moves the selected clip up in the list."""
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            return
        
        index = selected_indices[0]
        if index > 0:
            file_path = self.clip_list.pop(index)
            self.clip_list.insert(index - 1, file_path)
            self.clip_listbox.delete(index)
            self.clip_listbox.insert(index - 1, os.path.basename(file_path))
            
            self.clip_listbox.selection_clear(0, tk.END)
            self.clip_listbox.selection_set(index - 1)
            self.play_video(file_path)

    def move_down(self):
        """Moves the selected clip down in the list."""
        selected_indices = self.clip_listbox.curselection()
        if not selected_indices:
            return
        
        index = selected_indices[0]
        if index < len(self.clip_list) - 1:
            file_path = self.clip_list.pop(index)
            self.clip_list.insert(index + 1, file_path)
            self.clip_listbox.delete(index)
            self.clip_listbox.insert(index + 1, os.path.basename(file_path))

            self.clip_listbox.selection_clear(0, tk.END)
            self.clip_listbox.selection_set(index + 1)
            self.play_video(file_path)
            
    def merge_clips(self):
        """Initiates the process of merging clips."""
        if not self.clip_list:
            messagebox.showerror("Error", "Please add at least one clip to merge.")
            return

        output_dir = "merged_clips"
        os.makedirs(output_dir, exist_ok=True)
        base_name = "merged_video"
        extension = ".mp4"
        
        counter = 1
        output_file_name = f"{base_name}{extension}"
        output_path = os.path.join(output_dir, output_file_name)
        
        while os.path.exists(output_path):
            output_file_name = f"{base_name}_{counter}{extension}"
            output_path = os.path.join(output_dir, output_file_name)
            counter += 1

        threading.Thread(target=self._run_merge_clips, args=(output_path,)).start()

    def _run_merge_clips(self, output_file_path):
        """Internal function to handle the merging process."""
        try:
            caps = [cv2.VideoCapture(clip) for clip in self.clip_list]
            if not all(cap.isOpened() for cap in caps):
                messagebox.showerror("Error", "Failed to open one or more video files.")
                for cap in caps:
                    cap.release()
                return

            frame_width = int(caps[0].get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(caps[0].get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = caps[0].get(cv2.CAP_PROP_FPS)

            for cap in caps[1:]:
                if int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) != frame_width or \
                   int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) != frame_height:
                    messagebox.showerror("Error", "All videos must have the same dimensions to be merged.")
                    for c in caps: c.release()
                    return

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file_path, fourcc, fps, (frame_width, frame_height))

            if not out.isOpened():
                messagebox.showerror("Error", "Could not create the output video file. Check codec compatibility.")
                for c in caps: c.release()
                return
            
            for cap in caps:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                cap.release()

            out.release()
            messagebox.showinfo("Success", f"Clips successfully merged into '{output_file_path}'.")

        except Exception as e:
            messagebox.showerror("Merging Error", f"An error occurred during merging: {e}")
        finally:
            if 'caps' in locals():
                for cap in caps:
                    if cap and cap.isOpened():
                        cap.release()
            if 'out' in locals():
                out.release()
                
if __name__ == "__main__":
    app = VideoUtilityApp()
    app.mainloop()
