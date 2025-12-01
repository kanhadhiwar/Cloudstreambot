import os
import threading
import requests
from pathlib import Path
from flask import Flask, send_from_directory, abort
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

# ================= CONFIG =================
BOT_TOKEN = "8358684642:AAHntcN33numPcvFpsRICAhuL31DkH3Qn8Y"
TELE_API = "https://api.telegram.org"
VIDEO_DIR = "videos"

os.makedirs(VIDEO_DIR, exist_ok=True)

# ================= FLASK SERVER =================
app = Flask(__name__)

@app.route("/watch/<path:file>")
def stream(file):
    path = Path(VIDEO_DIR)/file
    if not path.exists():
        abort(404)
    return send_from_directory(VIDEO_DIR, file, mimetype="video/mp4")

@app.route("/download/<path:file>")
def download(file):
    path = Path(VIDEO_DIR)/file
    if not path.exists():
        abort(404)
    return send_from_directory(VIDEO_DIR, file, as_attachment=True)

def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# ================= TELEGRAM BOT HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Active ✅\nSend/forward any video → Streaming link milega!")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file_id = None
    unique = None
    ext = ".mp4"

    if msg.video:
        file_id = msg.video.file_id
        unique = msg.video.file_unique_id
    elif msg.document and msg.document.mime_type.startswith("video/"):
        file_id = msg.document.file_id
        unique = msg.document.file_unique_id
        ext = Path(msg.document.file_name).suffix or ".mp4"
    else:
        await msg.reply_text("❌ Sirf video files supported!")
        return

    if not file_id or not unique:
        await msg.reply_text("❌ File read error")
        return

    processing = await msg.reply_text("🔄 Downloading...")

    # ========== FILE PATH API ==========
    info = requests.get(f"{TELE_API}/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    if not info.get("ok"):
        await processing.edit_text("❌ Telegram file path not found")
        return

    path = info["result"]["file_path"]
    url = f"{TELE_API}/file/bot{BOT_TOKEN}/{path}"

    save = f"{unique}{ext}"
    save_path = Path(VIDEO_DIR)/save

    # ========== DOWNLOAD ==========
    file = requests.get(url, stream=True)
    total = int(file.headers.get("content-length", 0))
    down = 0
    chunk = 1024*256  # 256kb

    with open(save_path, "wb") as f:
        for data in file.iter_content(chunk):
            down += len(data)
            f.write(data)
            per = int((down/total)*100) if total else 0
            if per % 25 == 0:
                try:
                    await processing.edit_text(f"⬇️ Downloading... {per}%")
                except:
                    pass

    # ========== FINAL LINKS ==========
    stream_link = f"{BASE_URL}/watch/{save}"
    dl_link = f"{BASE_URL}/download/{save}"

    await processing.edit_text("✅ Link Ready!")

    await msg.reply_text(
        "🎬 *Your Streaming Link ✅*\n\n"
        f"▶️ Stream: {stream_link}\n"
        f"📥 Download: {dl_link}",
        parse_mode="Markdown"
    )

# ================= RUN BOT + SERVER =================
def bot_run():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_media))
    bot.run_polling()

threading.Thread(target=run, daemon=True).start()
threading.Thread(target=bot_run, daemon=True).start()

print("🤖 Cloud Stream Bot Running ✅")
