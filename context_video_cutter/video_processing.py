import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import shutil
from tkinter import messagebox

import pysrt
import toml
from pysrt import SubRipTime, SubRipFile
from slugify import slugify

import context_video_cutter.config_manager as config_manager
import context_video_cutter.utils as utils

BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "config.toml"
template_path = BASE_DIR / "config.example.toml"
if not config_path.exists():
    print("⚠ config.toml not found — creating from template.")
    shutil.copy(template_path, config_path)

config = toml.load(config_path)


def cut_video(labels, log_box, tk):
    if not config_manager.get_source_file_path():
        messagebox.showerror("Error", "Select video file.")
        return
    video = Path(config_manager.get_source_file_path())
    labels["clip_cutting_label"].config(text="Status: In progress", style="Blue.TLabel")
    base_name = slugify(Path(video).stem)
    current_output_dir = (
        BASE_DIR
        / config["paths"]["output_dir_base"]
        / datetime.today().strftime("%d.%m.%Y")
        / base_name
    )

    clips = []
    clips_statuses = []
    os.makedirs(current_output_dir, exist_ok=True)
    json_info = []

    text_box_value = labels["timecodes_textbox"].get("1.0", tk.END)
    if text_box_value:
        lines = text_box_value.strip().splitlines()
    else:
        lines = config_manager.get_timecodes()
    for i, line in enumerate(lines, 1):
        try:
            start, end = line.strip().split(" - ")
            clip_path = current_output_dir / f"clip_{i:02d}{video.suffix}"

            clips.append(clip_path)
            clips_statuses.append("Not started")

            json_info.append(
                {"filename": clip_path.as_posix(), "start": start, "end": end}
            )

            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                start,
                "-to",
                end,
                "-i",
                video,
                "-c",
                "copy",
                clip_path.as_posix(),
            ]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8"
            )
            for output_line in process.stdout:
                utils.log_message(message=output_line.strip(), log_box=log_box, tk=tk)
            process.wait()
        except Exception as e:
            messagebox.showwarning("Error", f"Wrong string format: {line}\n{e}")

    labels["embedding_clips_label"].config(
        text="\n".join([Path(v).name for v in clips])
    )
    labels["embedding_clips_statuses_label"].config(
        text="\n".join([v for v in clips_statuses])
    )

    clips_json_path = current_output_dir / "clips.json"
    with open(clips_json_path, "w", encoding="utf-8") as f:
        json.dump(json_info, f, ensure_ascii=False, indent=4)
        f.close()
    config_manager.set_clips_json_path(clips_json_path)
    labels["clips_json"].config(text=clips_json_path.name)

    labels["clip_cutting_label"].config(text="Status: Ready", style="Green.TLabel")


def hardcode_subs(labels, log_box, tk):
    labels["embedding_clips_label"].config(style="Blue.TLabel")
    labels["embedding_clips_statuses_label"].config(style="Blue.TLabel")
    if not config_manager.get_clips_json_path():
        messagebox.showerror("Error", "Select json file")
        return
    if not config_manager.get_subs_file_path():
        messagebox.showerror("Error", "Select subs file")
        return
    json_path = Path(config_manager.get_clips_json_path())
    subs_path = Path(config_manager.get_subs_file_path())

    with open(json_path, "r", encoding="utf-8") as f:
        clip_times = json.load(f)
        f.close()
    subs = pysrt.open(subs_path)

    clips_statuses = []
    for clip_info in clip_times:
        clips_statuses.append("Not started")

    account_info = config_manager.get_account_config()
    json_file = account_info["json"]

    for index, clip_info in enumerate(clip_times):
        clips_statuses[index] = "Processing"
        labels["embedding_clips_statuses_label"].config(
            text="\n".join([v for v in clips_statuses])
        )

        clip_file_path = Path(clip_info["filename"])

        start = SubRipTime.from_string(clip_info["start"])
        end = SubRipTime.from_string(clip_info["end"])

        clip_items = [s for s in subs if not (s.end <= start or s.start >= end)]
        clip = SubRipFile(items=clip_items)
        clip.shift(
            hours=-start.hours,
            minutes=-start.minutes,
            seconds=-start.seconds,
            milliseconds=-start.milliseconds,
        )
        clip.clean_indexes()
        temp_srt_path = clip_file_path.with_suffix(".srt")
        clip.save(temp_srt_path, encoding="utf-8")

        with open(json_file, 'r', encoding='utf-8') as f:
            account_json_file_data = json.load(f)
            f.close()

        account_json_file_data.append({
            "video": clip_info["filename"],
            "name": "",
            "hashtags": "",
            "is_uploaded": False,
            "uploaded_date": "",
        })

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(account_json_file_data, f, ensure_ascii=False, indent=4)
            f.close()

        # tmp_embed_video = Path(clip_file_path.as_posix()).with_stem(
        #     f"embed_clip_{index + 1}"
        # )
        #
        # cmd = [
        #     "ffmpeg",
        #     "-y",
        #     "-i",
        #     clip_file_path.as_posix(),
        #     "-vf",
        #     f"subtitles='{temp_srt_path.name}'",
        #     "-c:a",
        #     "copy",
        #     tmp_embed_video.as_posix(),
        # ]
        #
        # process = subprocess.Popen(
        #     cmd,
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT,
        #     encoding="utf-8",
        #     cwd=Path(clip_file_path).parent.as_posix(),
        # )
        # for line in process.stdout:
        #     utils.log_message(message=line.strip(), log_box=log_box, tk=tk)
        # process.wait()

        clips_statuses[index] = "Ready"
        labels["embedding_clips_statuses_label"].config(
            text="\n".join([v for v in clips_statuses])
        )

    labels["embedding_clips_label"].config(style="Green.TLabel")
    labels["embedding_clips_statuses_label"].config(style="Green.TLabel")
