import easyocr
import pygetwindow as gw
import cv2
import numpy as np
import mss
import time
import requests
import json
import os
from datetime import datetime
from difflib import SequenceMatcher
BOT_TOKEN     = '' # create telegram bot using BotFather and get bot token
CHAT_ID       = '' # get chat id where you want to send messages to (you can do that using getmyid bot in telegram)
NICKNAME      = "" # insert any nickname to customise messages
TRIGGERS_PATH = "triggers.json"

DEBUG_MODE    = False # enable if you want to adjust script settings like fuzzy_match
analysis_region = None
SCALE_FACTOR   = 2.5
fuzzy_tresh = 0.6 # this will allow triggers to be not exact, sometimes OCR cant fully recognise trigger phrase

reader = easyocr.Reader(['en'], gpu=False)

with open(TRIGGERS_PATH, "r", encoding="utf-8") as f:
    triggers = json.load(f)

active_triggers = set()

if DEBUG_MODE:
    os.makedirs("debug", exist_ok=True)


def get_game_window(title_contains):
    windows = gw.getWindowsWithTitle(title_contains)
    return windows[0] if windows else None


def preprocess_full_window(window):
    x, y, w, h = window.left, window.top, window.width, window.height
    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        screenshot = sct.grab(monitor)
        raw_img = np.array(screenshot)
        raw_img = cv2.cvtColor(raw_img, cv2.COLOR_BGRA2BGR)

    scaled = cv2.resize(raw_img, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    proc_img = clahe.apply(gray)

    return raw_img, proc_img


def select_analysis_region(window):
    raw_img, proc_img = preprocess_full_window(window)
    cv2.namedWindow("Select ROI (Processed)", cv2.WINDOW_NORMAL)
    max_display_w = min(proc_img.shape[1], 1920)
    max_display_h = min(proc_img.shape[0], 1080)
    cv2.resizeWindow("Select ROI (Processed)", max_display_w, max_display_h)

    roi = cv2.selectROI("Select ROI (Processed)", proc_img, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow("Select ROI (Processed)")

    x_scaled, y_scaled, w_scaled, h_scaled = roi

    x_orig = int(x_scaled / SCALE_FACTOR)
    y_orig = int(y_scaled / SCALE_FACTOR)
    w_orig = int(w_scaled / SCALE_FACTOR)
    h_orig = int(h_scaled / SCALE_FACTOR)

    return (x_orig, y_orig, w_orig, h_orig)


def preprocess_for_ocr(img):
    img_scaled = cv2.resize(img, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img_scaled, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl1 = clahe.apply(gray)
    return cl1


def extract_text_with_easyocr(window, region):
    if window.isMinimized:
        return []

    x_win, y_win = window.left, window.top
    x_offset, y_offset, sel_w, sel_h = region

    abs_left = x_win + x_offset
    abs_top  = y_win + y_offset
    abs_w    = sel_w
    abs_h    = sel_h

    with mss.mss() as sct:
        monitor = {"left": abs_left, "top": abs_top, "width": abs_w, "height": abs_h}
        screenshot = sct.grab(monitor)
        raw_crop = np.array(screenshot)
        raw_crop = cv2.cvtColor(raw_crop, cv2.COLOR_BGRA2BGR)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if DEBUG_MODE:
            raw_path = os.path.join("debug", f"raw_crop_{timestamp}.png")
            cv2.imwrite(raw_path, raw_crop)

        proc_crop = preprocess_for_ocr(raw_crop)

        if DEBUG_MODE:
            proc_path = os.path.join("debug", f"proc_crop_{timestamp}.png")
            cv2.imwrite(proc_path, proc_crop)

        text_lines = reader.readtext(proc_crop, detail=0)

        if DEBUG_MODE:
            print("----- [DEBUG] OCR Recognized Lines -----")
            if text_lines:
                for line in text_lines:
                    print(line)
            else:
                print("[DEBUG] No text detected.")
            print("----------------------------------------")

        return text_lines


def send_telegram_message(message, file_id=None):
    full_message = f"{NICKNAME} \"{message}\""
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": full_message}
    )
    if file_id:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "photo": file_id}
        )

def fuzzy_match(trigger_phrase, text_line, threshold=fuzzy_tresh):

    ratio = SequenceMatcher(None, trigger_phrase.lower(), text_line.lower()).ratio()
    return ratio >= threshold


def check_triggers(text_lines):
    global active_triggers
    for trigger in triggers:
        phrase = trigger["phrase"]
        message = trigger["message"]
        file_id = trigger.get("file_id")

        match_found = any(fuzzy_match(phrase, line) for line in text_lines)

        if match_found and phrase not in active_triggers:
            print(f"[✅] New trigger matched: «{phrase}» – sending message.")
            send_telegram_message(message, file_id)
            active_triggers.add(phrase)

        elif not match_found and phrase in active_triggers:
            active_triggers.remove(phrase)


if __name__ == "__main__":
    window_title = "window_name" #insert window name here
    window = get_game_window(window_title)

    if not window:
        print(f"No window with title containing \"{window_title}\" found. Please make sure the game is running.")
        exit(1)

    print("Please select the screen region for OCR (after scaling and CLAHE).")
    try:
        analysis_region = select_analysis_region(window)
    except Exception as e:
        print("Failed to open ROI selection window:", e)
        print("Use manual coordinate input or reinstall OpenCV with GUI support.")
        exit(1)

    if analysis_region[2] == 0 or analysis_region[3] == 0:
        print("No region selected or region too small. Restart the script and select a valid area.")
        exit(1)

    print(f"Selected analysis region (original coordinates): x_offset={analysis_region[0]}, "
          f"y_offset={analysis_region[1]}, width={analysis_region[2]}, height={analysis_region[3]}")

    try:
        while True:
            text_lines = extract_text_with_easyocr(window, analysis_region)
            if text_lines:
                check_triggers(text_lines)
            time.sleep(1)

    except KeyboardInterrupt:
        print("Script interrupted by user.")
        exit(0)
