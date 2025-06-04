# Event Analyzer
This is a Python script that analyzes events in a program/game with optical character recognition using [EasyOCR](https://github.com/JaidedAI/EasyOCR) and sends Telegram messages when predefined trigger phrases appear on screen.
## Features
Real-time OCR: Continuously captures and processes a user-defined region of a window.

Fuzzy Matching: Detects trigger phrases even if OCR is not 100% accurate (configurable threshold).

Telegram Alerts: Sends customized messages (and optional images) to a Telegram chat via a bot.

Debug Mode: Save raw and processed crops for tuning OCR and region selection.

## Libraries
[Python 3.7+]

easyocr — OCR engine

pygetwindow — Window enumeration and control

mss — Fast screenshot capture

opencv-python — Image processing (CLAHE, resizing)

numpy — Array manipulation

requests — HTTP requests to Telegram API

## Setup
```bash
1. Clone the repository

   git clone https://github.com/oxdarap/PET-projects.git
   cd Event_analyzer
   
3. Install dependencies

   pip install -r requirements.txt
   
4. Create Telegram Bot & Chat
Create a bot via BotFather and note down the BOT_TOKEN.
Use a helper bot like @getmyidbot to obtain your CHAT_ID.

5. Configure triggers

Edit triggers.json to include an array of any trigger objects that you want:
[
  {
    "phrase": "Boss Arrived",
    "message": "The boss has spawned!",
    "file_id": "<optional-telegram-photo-file_id>"
  },
  ...
]
```
## Troubleshooting
No window found: Verify the window_title contains the correct substring of your window’s title.

Region selection fails: Ensure OpenCV is installed with GUI support. On Linux, you may need sudo apt-get install libgtk2.0-dev.

OCR errors: Enable DEBUG_MODE = True to save raw and processed crops in /debug and inspect them.

No Telegram messages: Double-check BOT_TOKEN and CHAT_ID. Review Telegram API responses by temporarily printing response.text in send_telegram_message().

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE)