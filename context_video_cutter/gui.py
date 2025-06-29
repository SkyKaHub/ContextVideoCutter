import threading
import tkinter as tk
from pathlib import Path
import shutil
from tkinter import ttk

import context_video_cutter.subtitle_processing as subtitle_processing
import toml
import context_video_cutter.utils as utils
import context_video_cutter.video_processing as video_processing
from context_video_cutter import uploader
from context_video_cutter.config_manager import set_language, set_account, get_account_config

BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "config.toml"
template_path = BASE_DIR / "config.example.toml"
if not config_path.exists():
    print("⚠ config.toml not found — creating from template.")
    shutil.copy(template_path, config_path)

config = toml.load(config_path)
BASE_OUTPUT_DIR = (BASE_DIR / config["paths"]["output_dir_base"]).as_posix()
SOURCES_DIR = (BASE_DIR / config["paths"]["sources_dir"]).as_posix()


def create_app():
    app = tk.Tk()
    app.title("SkyCutter")
    app.geometry("1200x700")

    style = ttk.Style()
    style.configure("Blue.TLabel", foreground="blue")
    style.configure("Green.TLabel", foreground="green")

    # === Notebook ===
    notebook = ttk.Notebook(app)
    notebook.pack(fill="both", expand=True)

    # ==================== Tab 1: Tik Tok ==============================
    tiktok_tab = ttk.Frame(notebook)
    notebook.add(tiktok_tab, text="Tik Tok")

    # === Main layout with two columns ===
    tik_tok_main_frame = add_main_frame(tiktok_tab)

    # === Left: scrollable ===
    tik_tok_left_scrollable_frame = add_scrollable_frame(tik_tok_main_frame)

    # === Right: static (logs) ===
    right_frame = add_static_frame(tik_tok_main_frame)

    tik_tok_log_box = add_log_box(right_frame)

    # === Section: Account Selection ===
    tik_tok_account_selection_frame = ttk.LabelFrame(tik_tok_left_scrollable_frame, text="1. Select Account")
    tik_tok_account_selection_frame.pack(fill="x", padx=10, pady=10)

    tik_tok_account = tk.StringVar(value=config["default"]["account"])
    tik_tok_account.trace_add("write", lambda *_: set_account(tik_tok_account.get()))
    ttk.Label(tik_tok_account_selection_frame, text="Select tik_tok_account:").grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
    for idx, account_name in enumerate(config['accounts']):
        acc_data = config['accounts'][account_name]
        tk.Radiobutton(
            tik_tok_account_selection_frame,
            text=acc_data['accountname'],
            variable=tik_tok_account,
            value=account_name
        ).grid(row=0, column=idx, sticky="w")

    # === Section: Video Input ===
    tik_tok_video_frame = ttk.LabelFrame(tik_tok_left_scrollable_frame, text="2. Video Input")
    tik_tok_video_frame.pack(fill="x", padx=10, pady=10)

    tik_tok_language = tk.StringVar(value=config["default"]["language"])
    tik_tok_language.trace_add("write", lambda *_: set_language(tik_tok_language.get()))
    ttk.Label(tik_tok_video_frame, text="Select video language:").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=5
    )
    tk.Radiobutton(tik_tok_video_frame, text="English", variable=tik_tok_language, value="en").grid(
        row=2, column=1, sticky="w"
    )
    tk.Radiobutton(tik_tok_video_frame, text="Russian", variable=tik_tok_language, value="ru").grid(
        row=2, column=0, sticky="w"
    )

    ttk.Button(
        tik_tok_video_frame,
        text="Choose video for subtitles",
        command=lambda: utils.select_file(
            file_type="source", file_label=tik_tok_selected_file_label
        ),
    ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
    tik_tok_selected_file_label = ttk.Label(
        tik_tok_video_frame, text="No file selected", foreground="red"
    )
    tik_tok_selected_file_label.grid(row=4, column=0, columnspan=2, sticky="w")

    ttk.Label(tik_tok_video_frame, text="Or paste a YouTube link:").grid(
        row=5, column=0, columnspan=2, sticky="w", pady=5
    )
    tik_tok_url_entry = ttk.Entry(tik_tok_video_frame, width=50)
    tik_tok_url_entry.grid(row=6, column=0, columnspan=2, sticky="ew")

    tik_tok_url_button_frame = ttk.Frame(tik_tok_video_frame)
    tik_tok_url_button_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(5, 10))
    ttk.Button(
        tik_tok_url_button_frame,
        text="Download",
        command=lambda: utils.download_video(
            url=tik_tok_url_entry.get().strip(),
            log_box=tik_tok_log_box,
            tk=tk,
            labels={
                "downloaded_file_label": tik_tok_downloaded_file_label,
                "selected_file_label": tik_tok_selected_file_label,
            },
        ),
    ).pack(side="left", padx=(0, 5))
    ttk.Button(
        tik_tok_url_button_frame,
        text="Open source folder",
        command=lambda: utils.open_folder(SOURCES_DIR),
    ).pack(side="left", padx=(0, 5))
    tik_tok_downloaded_file_label = ttk.Label(
        tik_tok_url_button_frame, text="Not downloaded", foreground="red"
    )
    tik_tok_downloaded_file_label.pack(side="left", padx=(0, 5))

    # === Section: Subtitles ===
    tik_tok_subs_frame = ttk.LabelFrame(tik_tok_left_scrollable_frame, text="3. Subtitles")
    tik_tok_subs_frame.pack(fill="x", padx=10, pady=10)

    ttk.Button(
        tik_tok_subs_frame,
        text="Choose subs file",
        command=lambda: utils.select_file(
            file_type="subs", file_label=tik_tok_selected_subs_label
        ),
    ).grid(row=1, column=0, columnspan=1, sticky="ew", pady=5)

    tik_tok_selected_subs_label = ttk.Label(
        tik_tok_subs_frame, text="No file selected", foreground="red"
    )
    tik_tok_selected_subs_label.grid(row=1, column=1, columnspan=2, sticky="w", pady=5)

    ttk.Button(
        tik_tok_subs_frame,
        text="Generate Subtitles",
        command=lambda: subtitle_processing.transcribe_video(
            labels={
                "subtitle_label": tik_tok_subtitle_label,
                "selected_subs_label": tik_tok_selected_subs_label,
            },
            log_box=tik_tok_log_box,
            tk=tk,
        ),
    ).grid(row=0, column=0, sticky="w", pady=5)
    tik_tok_subtitle_label = ttk.Label(tik_tok_subs_frame, text="Status: Not started")
    tik_tok_subtitle_label.grid(row=0, column=1, sticky="w")

    # === Section: Detect interesting moments ===
    tik_tok_interesting_frame = ttk.LabelFrame(
        tik_tok_left_scrollable_frame, text="4. Interesting moments"
    )
    tik_tok_interesting_frame.pack(fill="x", padx=10, pady=10)



    tik_tok_interests_status_label = ttk.Label(
        tik_tok_interesting_frame, text="Not started", foreground="red"
    )
    tik_tok_interests_status_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

    ttk.Button(
        tik_tok_interesting_frame,
        text="Detect moments",
        command=lambda: threading.Thread(
            target=subtitle_processing.get_interests,
            args=(tik_tok_interests_status_label, tik_tok_timecodes_textbox, tk),  # её аргументы
            daemon=True,
        ).start(),
    ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

    # === Section: Clip Cutting ===
    tik_tok_cut_frame = ttk.LabelFrame(tik_tok_left_scrollable_frame, text="5. Clip Cutting")
    tik_tok_cut_frame.pack(fill="x", padx=10, pady=10)

    ttk.Label(tik_tok_cut_frame, text="Timecodes (format: 00:00:00.000 - 00:00:10.000):").grid(
        row=0, column=0, sticky="w"
    )
    tik_tok_timecodes_textbox = tk.Text(tik_tok_cut_frame, height=5, width=40)
    tik_tok_timecodes_textbox.grid(row=1, column=0, columnspan=2, sticky="ew")
    tik_tok_clip_cutting_label = ttk.Label(tik_tok_cut_frame, text="Not started")
    tik_tok_clip_cutting_label.grid(row=2, column=1, sticky="w", pady=5)
    ttk.Button(
        tik_tok_cut_frame,
        text="Cut Clips",
        command=lambda: threading.Thread(
            target=video_processing.cut_video,
            args=(
                {
                    "clip_cutting_label": tik_tok_clip_cutting_label,
                    "clips_json": tik_tok_clips_json_label,
                    "embedding_clips_label": tik_tok_embedding_clips_label,
                    "embedding_clips_statuses_label": tik_tok_embedding_clips_statuses_label,
                    "timecodes_textbox": tik_tok_timecodes_textbox,
                },
                tik_tok_log_box,
                tk,
            ),
            daemon=True,
        ).start(),
    ).grid(row=2, column=0, sticky="w", pady=5)

    # === Section: Subtitle Embedding ===
    tik_tok_convert_frame = ttk.LabelFrame(tik_tok_left_scrollable_frame, text="6. Subtitle Embedding")
    tik_tok_convert_frame.pack(fill="x", padx=10, pady=10)
    ttk.Button(
        tik_tok_convert_frame,
        text="Select JSON file",
        command=lambda: utils.select_file(
            file_type="clips_json",
            file_label=tik_tok_clips_json_label,
            additional_labels={
                "embedding_clips_label": tik_tok_embedding_clips_label,
                "embedding_clips_statuses_label": tik_tok_embedding_clips_statuses_label,
            },
        ),
    ).grid(row=0, column=0, sticky="w", pady=5)
    tik_tok_clips_json_label = ttk.Label(
        tik_tok_convert_frame, text="No JSON selected", style="Red.TLabel"
    )
    tik_tok_clips_json_label.grid(row=0, column=1, sticky="w", pady=5)

    tik_tok_embedding_clips_label = ttk.Label(
        tik_tok_convert_frame, text="No clips", style="Red.TLabel"
    )
    tik_tok_embedding_clips_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
    tik_tok_embedding_clips_statuses_label = ttk.Label(
        tik_tok_convert_frame, text="Not started", style="Red.TLabel"
    )
    tik_tok_embedding_clips_statuses_label.grid(
        row=1, column=2, columnspan=2, sticky="w", pady=5
    )
    ttk.Button(
        tik_tok_convert_frame,
        text="Embed Subtitles",
        command=lambda: threading.Thread(
            target=video_processing.hardcode_subs,
            args=(
                {
                    "embedding_clips_label": tik_tok_embedding_clips_label,
                    "embedding_clips_statuses_label": tik_tok_embedding_clips_statuses_label,
                },
                tik_tok_log_box,
                tk,
            ),
            daemon=True,
        ).start(),
    ).grid(row=2, column=0, sticky="w", pady=5)

    # === Section: TikTok Upload ===

    tik_tok_upload_frame = ttk.LabelFrame(tik_tok_left_scrollable_frame, text="7. TikTok Upload")
    tik_tok_upload_frame.pack(fill="x", padx=10, pady=10)

    ttk.Button(tik_tok_upload_frame, command=lambda: threading.Thread(
        target=uploader.get_left_videos_count,
        args=(
            tik_tok_get_count_label,
        ),
        daemon=True,
    ).start(), text="Get left count").grid(row=1, column=0, sticky="w", pady=5)
    tik_tok_get_count_label = ttk.Label(
        tik_tok_upload_frame, text="0"
    )
    tik_tok_get_count_label.grid(
        row=1, column=1, columnspan=2, sticky="w", pady=5
    )
    tik_tok_count_entry = ttk.Entry(
        tik_tok_upload_frame,
        width=10
    )
    tik_tok_count_entry.insert(0, "4")
    tik_tok_count_entry.grid(
        row=3, column=0, padx=5, pady=(0,5), sticky="w"
    )
    tik_tok_hours_between_entry = ttk.Entry(
        tik_tok_upload_frame,
        width=10
    )
    tik_tok_hours_between_entry.insert(0, "3")
    tik_tok_hours_between_entry.grid(
        row=3, column=1, padx=5, pady=(0,5), sticky="w"
    )
    ttk.Label(
        tik_tok_upload_frame, text="Videos count"
    ).grid(
        row=2, column=0, sticky="w", padx=5
    )
    ttk.Label(
        tik_tok_upload_frame, text="Hours between"
    ).grid(
        row=2, column=1, sticky="w", padx=5
    )
    ttk.Button(tik_tok_upload_frame, command=lambda: threading.Thread(
        target=uploader.upload_tik_tok_videos,
        args=(
            {
                "uploading_status_label": tik_tok_uploading_status_label,
                "tik_tok_count_entry" : tik_tok_count_entry,
                "tik_tok_hours_between_entry": tik_tok_hours_between_entry,
            },
            tik_tok_log_box,
            tk,
        ),
        daemon=True,
    ).start(), text="Upload to TikTok").grid(row=4, column=0, sticky="w", pady=5)
    tik_tok_uploading_status_label = ttk.Label(
        tik_tok_upload_frame, text="Not started", style="Red.TLabel"
    )
    tik_tok_uploading_status_label.grid(
        row=4, column=2, columnspan=2, sticky="w", pady=5
    )
    # ==================== Tab 1: Tik Tok ==============================

    # ==================== Tab 2: YouTube ====================
    youtube_tab = ttk.Frame(notebook)
    notebook.add(youtube_tab, text="YouTube")

    # === Main layout with two columns ===
    yt_main_frame = add_main_frame(youtube_tab)

    # === Left: scrollable ===
    yt_left_scrollable_frame = add_scrollable_frame(yt_main_frame)

    # === Right: static (logs) ===
    yt_right_frame = add_static_frame(yt_main_frame)

    yt_log_box = add_log_box(yt_right_frame)

    # ==================== Tab 2: YouTube ====================


    return app


def add_scrollable_frame(to_frame):
    left_canvas = tk.Canvas(to_frame)
    left_scrollbar = ttk.Scrollbar(
        to_frame, orient="vertical", command=left_canvas.yview
    )
    tik_tok_left_scrollable_frame = ttk.Frame(left_canvas)

    tik_tok_left_scrollable_frame.bind(
        "<Configure>",
        lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")),
    )

    left_canvas.create_window((0, 0), window=tik_tok_left_scrollable_frame, anchor="nw")
    left_canvas.configure(yscrollcommand=left_scrollbar.set)

    left_canvas.grid(row=0, column=0, sticky="nsew")
    left_scrollbar.grid(row=0, column=0, sticky="nse")

    return tik_tok_left_scrollable_frame

def add_main_frame(to_tab):
    frame = ttk.Frame(to_tab)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    return frame

def add_static_frame(to_frame):
    frame = ttk.Frame(to_frame)
    frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)
    return frame

def add_log_box(to_frame):
    frame = ttk.LabelFrame(to_frame, text="Logs")
    frame.grid(row=0, column=0, sticky="nsew")
    log_box = tk.Text(frame, height=40, wrap="word", state="disabled")
    log_box.pack(fill="both", expand=True)
    return log_box

if __name__ == "__main__":
    create_app()
