import os
import json
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# ===== إعدادات =====
FACEBOOK_PAGE_ACCESS_TOKEN = "EAAIa6hi80SEBO67X3ZCTEmssJ6ZCStx3nPNp8LMfdlvLICTJARzoobGkZAH0qzBQOkNaX0xUTeRIHCPVIG74MWOZANZAzY81yJ7BCavP3PX8eZBKMV56sHQ6lcUNLbs6YygVMO3V2JcNOqrRINsODdCS0SzowMlfDTmmZAjSIhDpbgOoZC7hgHv5EvI51fecZCylnYkGtAjIkJr3Cx2cwfwZDZD"
VERIFY_TOKEN = "oussama07"  # رمز تحقق مخصص
FACEBOOK_GRAPH_API_URL = 'https://graph.facebook.com/v11.0/me/messages'
AI_IMAGE_API = "http://185.158.132.66:2010/api/tnt/tnt-black-image"

# ===== تحميل بيانات المستخدمين =====
DATA_FILE = "facebook_users_data.json"
if os.path.exists(DATA_FILE):
    data = json.load(open(DATA_FILE, "r", encoding="utf-8"))
else:
    data = {"warnings": {}, "banned": {}}
warnings = data["warnings"]
banned_users = data["banned"]

bad_words = [
    "سكس","نيك","طيز","كس","قحبة","شرموطة","لعق","مص","بزاز","ممحونة",
    "فرج","عاهرة","لوطي","شاذ","جنس","اباحي","اغتصاب","مني","ممارسة"
]
BAN_DURATION = 7 * 24 * 60 * 60

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"warnings": warnings, "banned": banned_users}, f)

def send_facebook_message(user_id, text):
    url = FACEBOOK_GRAPH_API_URL
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {"recipient": {"id": user_id}, "message": {"text": text}}
    requests.post(url, params=params, headers=headers, json=data)

def send_facebook_image(user_id, img_url, caption=""):
    url = FACEBOOK_GRAPH_API_URL
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": user_id},
        "message": {
            "attachment": {"type": "image", "payload": {"url": img_url, "is_reusable": True}}
        }
    }
    requests.post(url, params=params, headers=headers, json=data)
    if caption:
        send_facebook_message(user_id, caption)

def generate_alert_image(text):
    try:
        r = requests.post(AI_IMAGE_API, json={"User-Prompt": text}, timeout=15)
        if r.status_code == 200:
            imgs = r.json().get("url-image", [])
            return imgs[0] if imgs else None
    except:
        return None

def handle_message(sender, text):
    uid = str(sender)
    lower_text = text.lower()

    # 🔴 التحقق من الحظر
    if uid in banned_users and time.time() < banned_users[uid]:
        send_facebook_message(sender, "🚫 تم حظرك لمدة أسبوع.")
        return

    # ✅ التحقق من الكلمات المسيئة
    if any(w in lower_text for w in bad_words):
        warnings[uid] = warnings.get(uid, 0) + 1
        if warnings[uid] >= 3:
            banned_users[uid] = time.time() + BAN_DURATION
            save_data()
            img = generate_alert_image("⛔ تم حظرك لمدة أسبوع بسبب الرسائل المسيئة")
            send_facebook_image(sender, img, "⛔ لقد تم حظرك لمدة أسبوع.")
        else:
            save_data()
            img = generate_alert_image(f"⚠️ تحذير {warnings[uid]}/3")
            send_facebook_image(sender, img, f"⚠️ تحذير {warnings[uid]}/3: تجنب الكلمات المسيئة!")
        return

    # ✅ ردود عادية
    if lower_text in ["سلام", "مرحبا", "hi", "hello"]:
        send_facebook_message(sender, "👋 أهلاً! أرسل وصف لنحول خيالك إلى صورة 🤯")
    else:
        send_facebook_message(sender, "⏳ جاري إنشاء الصورة...")
        img = generate_alert_image(text)
        if img:
            send_facebook_image(sender, img, "✅ تم الإنشاء! اكتب «المزيد» للاستكشاف.")
        else:
            send_facebook_message(sender, "❌ خطأ أثناء توليد الصورة.")

# ===== مسار تحقق Webhook من فيسبوك =====
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "❌ خطأ في Verify Token", 403

# ===== استقبال الرسائل من فيسبوك =====
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" in event:
                sender = event["sender"]["id"]
                text = event["message"].get("text", "")
                if text:
                    handle_message(sender, text)
    return "ok"

# ===== تشغيل على Render =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
