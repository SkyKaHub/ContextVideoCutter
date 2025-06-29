import threading
import os
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from tkinter import messagebox

import pysrt
import spacy

import toml
from sklearn.feature_extraction.text import TfidfVectorizer
from slugify import slugify

import context_video_cutter.utils as utils
import context_video_cutter.config_manager as config_manager

BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "config.toml"
template_path = BASE_DIR / "config.example.toml"
if not config_path.exists():
    print("⚠ config.toml not found — creating from template.")
    shutil.copy(template_path, config_path)

config = toml.load(config_path)


def transcribe_video(labels, log_box, tk):
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    video = config_manager.get_source_file_path()
    if not video:
        messagebox.showerror("Error", "Select video file")
        return

    labels["subtitle_label"].config(text="Status: In progress", style="Blue.TLabel")

    video_path = Path(video)
    base_name = slugify(video_path.stem)
    current_output_dir = (
        BASE_DIR
        / config["paths"]["output_dir_base"]
        / datetime.today().strftime("%d.%m.%Y")
        / base_name
    )
    os.makedirs(current_output_dir, exist_ok=True)
    output_wav = current_output_dir / f"{base_name}.wav"
    output_srt = current_output_dir / f"{base_name}.srt"

    def worker():
        try:
            utils.make_wav_from_video(
                input_video_path=video,
                output_audio_path=output_wav,
                log_box=log_box,
                tk=tk,
            )
            utils.make_srt_file_from_audio(
                input_file_path=output_wav,
                output_file_path=output_srt,
                log_box=log_box,
                tk=tk,
            )
            os.remove(output_wav)
            status_text = (
                "Status: Ready ✅" if output_srt.exists() else "Status: Not ready ❌"
            )
            fg_color = "green" if output_srt.exists() else "red"
            labels["subtitle_label"].after(
                0,
                lambda: labels["subtitle_label"].config(
                    text=status_text, foreground=fg_color
                ),
            )
            labels["selected_subs_label"].config(
                text=Path(output_srt).name, style="Green.TLabel"
            )
            config_manager.set_subs_file_path(output_srt)
        except Exception as e:
            labels["subtitle_label"].after(
                0,
                lambda: labels["subtitle_label"].config(
                    text=f"Error: {e}", foreground="red"
                ),
            )

    threading.Thread(target=worker, daemon=True).start()


import spacy
import numpy as np
import pysrt
from datetime import timedelta
from tkinter import messagebox


def get_interests(label, timecodes_textbox, tk, threshold: float = 0.5):
    label.config(text="Processing…", foreground="blue")

    segments = get_interest_segments(config_manager.get_subs_file_path(), config_manager.get_language())

    # build timecodes: from first start to last end in each segment
    interesting_timecodes = []
    for seg in segments:
        start = seg[0]["start"].strftime("%H:%M:%S") + ".000"
        end = seg[-1]["end"].strftime("%H:%M:%S") + ".000"
        interesting_timecodes.append(f"{start} - {end}")

    # save & display
    config_manager.set_timecodes(interesting_timecodes)

    if not interesting_timecodes:
        label.config(text="No timecodes", foreground="red")
    else:
        label.config(text="Done", foreground="green")
        timecodes_textbox.delete("1.0", tk.END)
        timecodes_textbox.insert("1.0", "\n".join(interesting_timecodes))

def get_interest_segments(srt_file, language="en", threshold: float = 0.7):

    if language == "ru":
        nlp = spacy.load("ru_core_news_sm")
    else:
        nlp = spacy.load("en_core_web_sm")

    # read .srt and build text blocks
    subs = pysrt.open(srt_file, encoding="utf-8")
    blocks = []
    buf_text = ""
    buf_start = None
    for sub in subs:
        if not buf_text:
            buf_start = sub.start.to_time()
        buf_text += sub.text + " "
        if sub.text.rstrip().endswith((".", "!", "?")):
            buf_end = sub.end.to_time()
            blocks.append(
                {
                    "text": buf_text.strip(),
                    "start": buf_start,
                    "end": buf_end,
                }
            )
            buf_text = ""

    # segment into topic‐coherent clusters
    segments = []
    current = []
    prev_vec = None
    min_duration = timedelta(minutes=1)

    for blk in blocks:
        vec = nlp(blk["text"]).vector
        if prev_vec is None:
            current = [blk]
        else:
            # cosine similarity
            sim = np.dot(prev_vec, vec) / (
                    np.linalg.norm(prev_vec) * np.linalg.norm(vec) + 1e-8
            )

            start = current[0]["start"]
            end = blk["end"]
            dur = timedelta(
                hours=end.hour, minutes=end.minute, seconds=end.second
            ) - timedelta(hours=start.hour, minutes=start.minute, seconds=start.second)

            if sim < threshold and dur >= min_duration:
                segments.append(current)
                current = [blk]
            else:
                current.append(blk)
        prev_vec = vec

    # append last
    if current:
        segments.append(current)

    segments = select_top_n_interesting(segments)

    return segments

def select_top_n_interesting(segments, n=10):
    texts = [" ".join(blk["text"] for blk in seg) for seg in segments]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf = vectorizer.fit_transform(texts)
    scores = np.asarray(tfidf.sum(axis=1)).ravel()
    top_idx = np.argsort(scores)[::-1][:n]
    top_idx_sorted = sorted(top_idx)
    return [segments[i] for i in top_idx_sorted]