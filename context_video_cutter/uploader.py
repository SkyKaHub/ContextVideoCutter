import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox
from tiktokautouploader import upload_tiktok

import toml

from context_video_cutter import utils
from context_video_cutter.config_manager import get_account_config

BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "config.toml"
template_path = BASE_DIR / "config.example.toml"
if not config_path.exists():
    print("⚠ config.toml not found — creating from template.")
    config = toml.load(template_path)
else:
    config = toml.load(config_path)

#Supported only ENG accounts!
def upload_tik_tok_videos(labels, log_box, tk):
    labels["uploading_status_label"].configure(foreground="blue", text="Processing...")
    account_info = get_account_config()
    json_file = account_info["json"]
    if Path(json_file).exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            account_json_file_data = json.load(f)
            f.close()
    else:
        account_json_file_data = []
    filtered_data = [item for item in account_json_file_data if item.get("is_uploaded") == False]
    if not filtered_data:
        messagebox.showerror("Ошибка", "Нет видео для заливки.")
        return

    now = datetime.now() + timedelta(minutes=20)
    # add 5 min to near number divided by 5
    extra = (5 - now.minute % 5) % 5
    schedule = now + timedelta(minutes=extra, seconds=-now.second, microseconds=-now.microsecond)

    original_stdout = sys.stdout
    sys.stdout = type('', (), {'write': lambda self, msg: utils.log_message(msg.strip(), log_box, tk), 'flush': lambda self: None})()

    for video in filtered_data[:labels["tik_tok_count_entry"].get()]:
        desc = video["name"]
        video_path = video["video"]
        accountname = account_info["accountname"]
        utils.log_message(upload_tiktok(video=video_path, description=desc,
                                  hashtags=[tag for tag in video["hashtags"].split() if tag.startswith("#")],
                                  accountname=accountname, schedule=schedule.strftime("%H:%M")), log_box, tk)
        video["is_uploaded"] = True
        video["uploaded_date"] = schedule.strftime("%Y-%m-%d %H:%M")
        schedule += timedelta(hours=labels["tik_tok_hours_between_entry"].get())

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(account_json_file_data, f, ensure_ascii=False, indent=4)
        f.close()
    sys.stdout = original_stdout

    labels["uploading_status_label"].configure(foreground="green", text="Done!")

def get_left_videos_count(label):
    account_info = get_account_config()
    json_file = account_info["json"]
    if Path(json_file).exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            account_json_file_data = json.load(f)
            f.close()
    else:
        account_json_file_data = []
    filtered_data = [item for item in account_json_file_data if item.get("is_uploaded") == False]
    label.config(text=len(filtered_data))