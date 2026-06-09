import asyncio
import io
import re
import json
import html
import os
import httpx
import random
import string
import time
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.request import HTTPXRequest

# ওটিপি কোড সরাসরি ওয়ান-ক্লিক কপি করার লাইব্রেরি ইম্পোর্ট
try:
    from telegram import CopyTextButton
    HAS_COPY_BTN = True
except ImportError:
    HAS_COPY_BTN = False

# ==================== CONFIG SECTION ====================

BOT_TOKEN = "8617265691:AAHqAWhc8q3no6ntRQKk2YUn9GQIyNcUoc0"
API_KEY = "MURAD_7BBC35C320D5D59C990FDC92"  # FastXOTP এপিআই কী
BASE_URL = "https://fastxotp.com"           # FastXOTP এপিআই ডোমেন
USER_DATA_FILE = "users.json"
PAID_SMS_FILE = "paid_sms.json"
STATS_FILE = "user_stats.json"
BANNED_USERS_FILE = "banned_users.json"
WITHDRAW_DATA_FILE = "withdraw_requests.json"
ACTIVITY_LOGS_FILE = "activity_logs.json"
DATA_RANGE_FILE = "datarange.json"
SETTINGS_FILE = "settings.json"

WELCOME_MESSAGE = (
    "✦ ━━━━━━━━━━━━━━━━━━━━━━━━ ✦\n"
    "    <b>FAST X OTP NUMBER BOT</b>\n"
    "✦ ━━━━━━━━━━━━━━━━━━━━━━━━ ✦\n\n"
    "👑 <b>Start Instant OTP Reception Now!</b>\n\n"
    "<blockquote>আমাদের প্রিমিয়াম ও সুপারফাস্ট গ্লোবাল ওটিপি সার্ভারে আপনাকে স্বাগতম। নম্বর নিতে নিচের কিবোর্ড বাটনগুলো ব্যবহার করুন।</blockquote>"
)

# ==================== SYSTEM DYNAMIC SETTINGS ====================

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        default = {
            "max_numbers_per_user": 10000,  # Max Numbers Per Batch
            "welcome_message": WELCOME_MESSAGE,
            "otp_group_url": "https://t.me/otpgroupsl",
            "channel_url": "https://t.me/instagramotp20",
            "support_username": "@insotpgrambotowner",
            "maintenance_mode": False,
            "min_withdraw": 0.5,
            "max_withdraw": 100.0,
            "api_key": API_KEY,
            "base_url": BASE_URL,
            "cooldown_time": 1.0,          # নম্বর চেঞ্জ লিমিট
            "force_join_enabled": False,   # ফোর্স জয়েন অন/অফ সিস্টেম
            "force_join_channels": ["@instagramotp20"], # ফোর্স জয়েন চ্যানেলসমূহ
            "join_alert_enabled": True,     # ম্যানুয়াল এডমিন জয়েন নোটিফিকেশন
            "otp_reward": 0.0020,          # প্রতি ওটিপিতে বোনাস
            "refer_bonus": 0.050,          # রেফারেল বোনাস
            "numbers_per_request": 3       # একসাথে কয়টি নাম্বার দিবে
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default, f, indent=1)
        return default
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            updated = False
            if "otp_reward" not in data:
                data["otp_reward"] = 0.0020
                updated = True
            if "refer_bonus" not in data:
                data["refer_bonus"] = 0.050
                updated = True
            if "numbers_per_request" not in data:
                data["numbers_per_request"] = 3
                updated = True
            if "min_withdraw" not in data or data["min_withdraw"] == 50:
                data["min_withdraw"] = 0.5
                updated = True
            if updated:
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(data, f, indent=1)
            return data
    except:
        return {
            "max_numbers_per_user": 10000,
            "welcome_message": WELCOME_MESSAGE,
            "otp_group_url": "https://t.me/+31eV11IT7WQzMjI9",
            "channel_url": "https://t.me/MinoXofficial0",
            "support_username": "@NETBOLDNETMAIR0",
            "maintenance_mode": False,
            "min_withdraw": 0.5,
            "max_withdraw": 100.0,
            "api_key": API_KEY,
            "base_url": BASE_URL,
            "cooldown_time": 1.0,
            "force_join_enabled": False,
            "force_join_channels": ["@MinoXofficial0"],
            "join_alert_enabled": True,
            "otp_reward": 0.0010,
            "refer_bonus": 0.0040,
            "numbers_per_request": 3
        }

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=1)

def get_api_credentials():
    settings = load_settings()
    return settings.get("api_key", API_KEY), settings.get("base_url", BASE_URL)

def get_withdraw_limits():
    settings = load_settings()
    return float(settings.get("min_withdraw", 0.5)), float(settings.get("max_withdraw", 100.0))

def is_under_maintenance(uid):
    settings = load_settings()
    return settings.get("maintenance_mode", False) and not is_admin(uid)

# ==================== FORCE JOIN HELPER FUNCTIONS ====================

async def is_user_joined_force_channels(uid, context):
    settings = load_settings()
    if not settings.get("force_join_enabled", False):
        return True
    channels = settings.get("force_join_channels", [])
    if not channels:
        return True
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=uid)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            print(f"Error checking force join for {channel}: {e}")
            return False
    return True

def build_force_join_keyboard():
    settings = load_settings()
    channels = settings.get("force_join_channels", [])
    keyboard = []
    for idx, channel in enumerate(channels, 1):
        clean_channel = channel.replace("@", "")
        url = f"https://t.me/{clean_channel}"
        keyboard.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=url, style="primary")])
    keyboard.append([InlineKeyboardButton("🔄 Check Join", callback_data="check_force_join", style="success")])
    return InlineKeyboardMarkup(keyboard)

# ==================== MULTIPLE ADMINS CONFIGURATION ====================
ADMINS = [6727558565]  

OTP_GROUP_ID = -1003767737552

request_queue = asyncio.Queue() 
MAX_WORKERS = 50000 

client_async = httpx.AsyncClient(
    timeout=10.0, 
    limits=httpx.Limits(max_connections=1000, max_keepalive_connections=200)
)

active_numbers = {}
last_range = {}
last_request_time = {} # ইউজার রিকোয়েস্ট কুলডাউন ট্র্যাকিং
CHECK_INTERVAL = 0.5  

# ==================== GLOBAL RANGES CACHE ====================
_ranges_cache = {"data": None, "updated_at": 0.0, "fetching": False}

def get_platform_icon(platform_name: str) -> str:
    return ""

# ডায়নামিক বোল্ড কনভার্টার
def make_bold_text(text: str) -> str:
    out = []
    for char in str(text):
        o = ord(char)
        if 65 <= o <= 90: # A-Z
            out.append(chr(o - 65 + 0x1D5D4))
        elif 97 <= o <= 122: # a-z
            out.append(chr(o - 97 + 0x1D5EE))
        elif 48 <= o <= 57: # 0-9
            out.append(chr(o - 48 + 0x1D7EC))
        else:
            out.append(char)
    return "".join(out)

async def _bg_refresh_ranges():
    global _ranges_cache
    while True:
        try:
            if not _ranges_cache["fetching"]:
                _ranges_cache["fetching"] = True
                try:
                    data, err = await fetch_top55_ranges_by_app()
                    if data:
                        import time as _time
                        _ranges_cache["data"] = data
                        _ranges_cache["updated_at"] = _time.monotonic()
                except Exception:
                    pass
                finally:
                    _ranges_cache["fetching"] = False
        except Exception:
            pass
        await asyncio.sleep(320) # স্লিপ টাইম: ৩২০ সেকেন্ড

# ==================== CHECK IF USER IS ADMIN ====================

def is_admin(user_id):
    return user_id in ADMINS

# ==================== WITHDRAW DATA FUNCTIONS ====================

def load_withdraw_requests():
    if not os.path.exists(WITHDRAW_DATA_FILE):
        with open(WITHDRAW_DATA_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(WITHDRAW_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_withdraw_requests(data):
    with open(WITHDRAW_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_payment_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

# ==================== BANNED USERS FUNCTIONS ====================

def load_banned_users():
    if not os.path.exists(BANNED_USERS_FILE):
        with open(BANNED_USERS_FILE, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(BANNED_USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_banned_users(banned_list):
    with open(BANNED_USERS_FILE, "w") as f:
        json.dump(banned_list, f, indent=4)

def is_user_banned(uid):
    banned_list = load_banned_users()
    return str(uid) in banned_list

def ban_user(uid):
    banned_list = load_banned_users()
    uid_str = str(uid)
    if uid_str not in banned_list:
        banned_list.append(uid_str)
        save_banned_users(banned_list)
        return True
    return False

def unban_user(uid):
    banned_list = load_banned_users()
    uid_str = str(uid)
    if uid_str in banned_list:
        banned_list.remove(uid_str)
        save_banned_users(banned_list)
        return True
    return False

# ==================== DATA RANGE FILE ====================

def load_range_db():
    if not os.path.exists(DATA_RANGE_FILE):
        return {}
    try:
        with open(DATA_RANGE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_range_db(data):
    with open(DATA_RANGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_number_range_info(uid, number, range_text):
    db = load_range_db()
    flag, name = get_country_info(number)
    db[normalize_number(number)] = {
        "user_id": str(uid),
        "number": f"+{normalize_number(number)}",
        "range": range_text,
        "country": f"{flag} {name}"
    }
    save_range_db(db)

# ==================== COUNTRY MAPPING SECTION ====================

def get_country_info(number):
    number = str(number).strip()
    
    country_map = {
        "2376": ("🇨🇲", "Cameroon"),
        "2250": ("🇨🇮", "Ivory Coast"),
        "2613": ("🇲🇬", "Madagascar"),
        "4077": ("🇷🇴", "Romania"),
        "447": ("🇬🇧", "UK (Virtual)"),
        "1201": ("🇺🇸", "USA (Virtual)"),
        "1302": ("🇺🇸", "USA (Virtual)"),
        "1415": ("🇺🇸", "USA (Virtual)"),
        "1212": ("🇺🇸", "USA (Virtual)"),
        "1917": ("🇺🇸", "USA (Virtual)"),
        "1646": ("🇺🇸", "USA (Virtual)"),
        "1347": ("🇺🇸", "USA (Virtual)"),
        "237": ("🇨🇲", "Cameroon"),
        "225": ("🇨🇮", "Ivory Coast"),
        "261": ("🇲🇬", "Madagascar"),
        "20": ("🇪🇬", "Egypt"),
        "27": ("🇿🇦", "South Africa"),
        "234": ("🇳🇬", "Nigeria"),
        "254": ("🇰🇪", "Kenya"),
        "233": ("🇬🇭", "Ghana"),
        "212": ("🇲🇦", "Morocco"),
        "213": ("🇩🇿", "Algeria"),
        "216": ("🇹🇳", "Tunisia"),
        "218": ("🇱🇾", "Libya"),
        "249": ("🇸🇩", "Sudan"),
        "251": ("🇪🇹", "Ethiopia"),
        "252": ("🇸🇴", "Somalia"),
        "253": ("🇩🇯", "Djibouti"),
        "255": ("🇹🇿", "Tanzania"),
        "256": ("🇺🇬", "Uganda"),
        "257": ("🇧🇮", "Burundi"),
        "258": ("🇲🇿", "Mozambique"),
        "260": ("🇿🇲", "Zambia"),
        "263": ("🇿🇼", "Zimbabwe"),
        "264": ("🇳🇦", "Namibia"),
        "265": ("🇲🇼", "Malawi"),
        "266": ("🇱🇸", "Lesotho"),
        "267": ("🇧🇼", "Botswana"),
        "268": ("🇸🇿", "Eswatini"),
        "269": ("🇰🇲", "Comoros"),
        "220": ("🇬🇲", "Gambia"),
        "221": ("🇸🇳", "Senegal"),
        "222": ("🇲🇷", "Mauritania"),
        "223": ("🇲🇱", "Mali"),
        "224": ("🇬🇳", "Guinea"),
        "226": ("🇧🇫", "Burkina Faso"),
        "227": ("🇳🇪", "Niger"),
        "228": ("🇹🇬", "Togo"),
        "229": ("🇧🇯", "Benin"),
        "230": ("🇲🇺", "Mauritius"),
        "231": ("🇱🇷", "Liberia"),
        "232": ("🇸🇱", "Sierra Leone"),
        "235": ("🇹🇩", "Chad"),
        "236": ("🇨🇫", "Central African Republic"),
        "238": ("🇨🇻", "Cape Verde"),
        "239": ("🇸🇹", "Sao Tome and Principe"),
        "240": ("🇬🇶", "Equatorial Guinea"),
        "241": ("🇬🇦", "Gabon"),
        "242": ("🇨🇬", "Congo"),
        "243": ("🇨🇩", "DR Congo"),
        "244": ("🇦🇴", "Angola"),
        "245": ("🇬🇼", "Guinea-Bissau"),
        "247": ("🇸🇭", "Saint Helena"),
        "248": ("🇸🇨", "Seychelles"),
        "250": ("🇷🇼", "Rwanda"),
        "290": ("🇸🇭", "Saint Helena"),
        "291": ("🇪🇷", "Eritrea"),
        "40": ("🇷🇴", "Romania"),
        "44": ("🇬🇧", "United Kingdom"),
        "33": ("🇫🇷", "France"),
        "49": ("🇩🇪", "Germany"),
        "39": ("🇮🇹", "Italy"),
        "34": ("🇪🇸", "Spain"),
        "31": ("🇳🇱", "Netherlands"),
        "32": ("🇧🇪", "Belgium"),
        "41": ("🇨🇭", "Switzerland"),
        "43": ("🇦🇹", "Austria"),
        "46": ("🇸🇪", "Sweden"),
        "47": ("🇳🇴", "Norway"),
        "45": ("🇩кем", "Denmark"),
        "358": ("🇫🇮", "Finland"),
        "351": ("🇵🇹", "Portugal"),
        "353": ("🇮🇪", "Ireland"),
        "36": ("🇭🇺", "Hungary"),
        "48": ("🇵🇱", "Poland"),
        "380": ("🇺🇦", "Ukraine"),
        "370": ("🇱🇹", "Lithuania"),
        "371": ("🇱🇻", "Latvia"),
        "372": ("🇪🇪", "Estonia"),
        "373": ("🇲🇩", "Moldova"),
        "374": ("🇦🇲", "Armenia"),
        "375": ("🇧🇾", "Belarus"),
        "376": ("🇦🇩", "Andorra"),
        "377": ("🇲🇨", "Monaco"),
        "378": ("🇸🇲", "San Marino"),
        "379": ("🇻🇦", "Vatican City"),
        "381": ("🇷🇸", "Serbia"),
        "382": ("🇲🇪", "Montenegro"),
        "383": ("🇽🇲", "Kosovo"),
        "385": ("🇭🇷", "Croatia"),
        "386": ("🇸🇮", "Slovenia"),
        "387": ("🇧🇦", "Bosnia and Herzegovina"),
        "389": ("🇲🇰", "North Macedonia"),
        "350": ("🇬🇮", "Gibraltar"),
        "352": ("🇱🇺", "Luxembourg"),
        "354": ("🇮🇸", "Iceland"),
        "355": ("🇦🇱", "Albania"),
        "356": ("🇲🇹", "Malta"),
        "357": ("🇨🇾", "Cyprus"),
        "359": ("🇧🇬", "Bulgaria"),
        "421": ("🇸🇰", "Slovakia"),
        "420": ("🇨🇿", "Czech Republic"),
        "298": ("🇫🇴", "Faroe Islands"),
        "299": ("🇬🇱", "Greenland"),
        "1": ("🇺🇸", "United States / Canada"),
        "7": ("🇷🇺", "Russia / Kazakhstan"),
        "880": ("🇧🇩", "Bangladesh"),
        "86": ("🇨🇳", "China"),
        "81": ("🇯🇵", "Japan"),
        "82": ("🇰🇷", "South Korea"),
        "84": ("🇻🇳", "Vietnam"),
        "66": ("🇹🇭", "Thailand"),
        "62": ("🇮🇩", "Indonesia"),
        "60": ("🇲🇾", "Malaysia"),
        "65": ("🇸🇬", "Singapore"),
        "63": ("🇵🇭", "Philippines"),
        "95": ("🇲🇲", "Myanmar"),
        "94": ("🇱🇰", "Sri Lanka"),
        "977": ("🇳🇵", "Nepal"),
        "93": ("🇦𝒇", "Afghanistan"),
        "98": ("🇮🇷", "Iran"),
        "90": ("🇹🇷", "Turkey"),
        "964": ("🇮🇶", "Iraq"),
        "963": ("🇸🇾", "Syria"),
        "961": ("🇱🇧", "Lebanon"),
        "962": ("🇯🇴", "Jordan"),
        "965": ("🇰🇼", "Kuwait"),
        "966": ("🇸🇦", "Saudi Arabia"),
        "967": ("🇾🇪", "Yemen"),
        "968": ("🇴🇲", "Oman"),
        "971": ("🇦🇪", "United Arab Emirates"),
        "972": ("🇮🇱", "Israel"),
        "973": ("🇧🇭", "Bahrain"),
        "974": ("🇶🇦", "Qatar"),
        "994": ("🇦🇿", "Azerbaijan"),
        "995": ("🇬🇪", "Georgia"),
        "996": ("🇰🇬", "Kyrgyzstan"),
        "992": ("🇹🇯", "Tajikistan"),
        "993": ("🇹🇲", "Turkmenistan"),
        "998": ("🇺🇿", "Uzbekistan"),
        "855": ("🇰🇭", "Cambodia"),
        "856": ("🇱🇦", "Laos"),
        "976": ("🇲🇳", "Mongolia"),
        "850": ("🇰🇵", "North Korea"),
        "55": ("🇧🇷", "Brazil"),
        "52": ("🇲🇽", "Mexico"),
        "54": ("🇦🇷", "Argentina"),
        "57": ("🇨🇴", "Colombia"),
        "51": ("🇵🇪", "Peru"),
        "58": ("🇻🇪", "Venezuela"),
        "56": ("🇨🇱", "Chile"),
        "593": ("🇪🇨", "Ecuador"),
        "591": ("🇧🇴", "Bolivia"),
        "595": ("🇵🇾", "Paraguay"),
        "598": ("🇺🇾", "Uruguay"),
        "502": ("🇬🇹", "Guatemala"),
        "503": ("🇸🇻", "El Salvador"),
        "504": ("🇭🇳", "Honduras"),
        "505": ("🇳🇮", "Nicaragua"),
        "506": ("🇨🇷", "Costa Rica"),
        "507": ("🇵🇦", "Panama"),
        "509": ("🇭🇹", "Haiti"),
        "501": ("🇧🇿", "Belize"),
        "61": ("🇦🇺", "Australia"),
        "64": ("🇳🇿", "New Zealand"),
        "675": ("🇵🇬", "Papua New Guinea"),
        "679": ("🇫จิต", "Fiji"),
        "685": ("🇼🇸", "Samoa"),
        "686": ("🇰🇮", "Kiribati"),
        "691": ("🇫🇲", "Micronesia"),
        "692": ("🇲🇭", "Marshall Islands"),
        "297": ("🇦🇼", "Aruba"),
        "1246": ("🇧🇧", "Barbados"),
        "1441": ("🇧🇲", "Bermuda"),
        "1345": ("🇰🇾", "Cayman Islands"),
        "53": ("🇨🇺", "Cuba"),
        "1473": ("🇬🇩", "Grenada"),
        "592": ("🇬🇾", "Guide"),
        "1876": ("🇯🇲", "Jamaica"),
        "1758": ("🇱🇨", "Saint Lucia"),
        "1784": ("🇻🇨", "Saint Vincent"),
        "1868": ("🇹🇹", "Trinidad and Tobago"),
    }
    
    clean_num = str(number).replace('+', '').replace(' ', '').replace('-', '').strip()
    sorted_prefixes = sorted(country_map.keys(), key=len, reverse=True)
    
    for prefix in sorted_prefixes:
        if clean_num.startswith(prefix):
            return country_map[prefix]
    
    return ("🇨🇮", "IVORY COAST")

def get_country_lang(country_name):
    country_lower = country_name.lower()
    if "egypt" in country_lower or "saudi" in country_lower or "yemen" in country_lower or "iraq" in country_lower or "sudan" in country_lower or "morocco" in country_lower or "algeria" in country_lower:
        return "Arabic"
    if "bangladesh" in country_lower:
        return "Bengali"
    if "russia" in country_lower or "kazakhstan" in country_lower:
        return "Russian"
    if "brazil" in country_lower:
        return "Portuguese"
    if "france" in country_lower:
        return "French"
    if "spain" in country_lower or "mexico" in country_lower or "argentina" in country_lower:
        return "Spanish"
    return "English"

# দেশের নামের ওপর ভিত্তি করে ২-অক্ষরের স্ট্যান্ডার্ড অ্যাব্রেভিয়েশন (যেমন: CA/CM) ফেরত পাওয়ার মেথড
def get_country_abbr(name: str) -> str:
    name_upper = name.upper()
    if "CAMEROON" in name_upper:
        return "CA"
    mappings = {
        "UNITED STATES": "US", "BANGLADESH": "BD", "UNITED KINGDOM": "UK",
        "ROMANIA": "RO", "MADAGASCAR": "MG", "IVORY COAST": "CI", "INDIA": "IN"
    }
    for k, v in mappings.items():
        if k in name_upper:
            return v
    return name_upper[:2]

# ==================== SERVICE DETECTION & CLEANING ====================

def get_clean_app_name(app_name: str) -> str:
    name_lower = app_name.lower().strip()
    if "facebook" in name_lower or name_lower == "fb":
        return "Facebook"
    if "instagram" in name_lower or "instragram" in name_lower or name_lower == "insta":
        return "Instagram"
    if "whatsapp" in name_lower or "whats app" in name_lower:
        return "WhatsApp"
    if "tiktok" in name_lower:
        return "TikTok"
    if "paypal" in name_lower:
        return "PayPal"
    if "telegram" in name_lower or name_lower == "tg":
        return "Telegram"
    if "discord" in name_lower:
        return "Discord"
    return app_name.capitalize()

def detect_service(full_sms):
    if not full_sms:
        return "SMS SERVICE"
    
    sms_lower = full_sms.lower()
    
    service_keywords = {
        "facebook": "FACEBOOK", "fb": "FACEBOOK", "instagram": "INSTAGRAM", "insta": "INSTAGRAM",
        "tiktok": "TIKTOK", "twitter": "TWITTER", "x.com": "TWITTER", "snapchat": "SNAPCHAT",
        "snap": "SNAPCHAT", "whatsapp": "WHATSAPP", "whats app": "WHATSAPP", "telegram": "TELEGRAM",
        "tg": "TELEGRAM", "discord": "DISCORD", "messenger": "MESSENGER", "linkedin": "LINKEDIN",
        "pinterest": "PINTEREST", "reddit": "REDDIT", "youtube": "YOUTUBE", "google": "GOOGLE",
        "gmail": "GOOGLE", "line": "LINE", "wechat": "WECHAT", "viber": "VIBER", "skype": "SKYPE",
        "signal": "SIGNAL", "imo": "IMO", "tumblr": "TUMBLR", "flickr": "FLICKR", "quora": "QUORA",
        "vk": "VK", "ok.ru": "OK", "odnoklassniki": "OK", "pubg": "PUBG", "free fire": "FREE FIRE",
        "freefire": "FREE FIRE", "call of duty": "CALL OF DUTY", "cod": "CALL OF DUTY",
        "fortnite": "FORTNITE", "minecraft": "MINECRAFT", "roblox": "ROBLOX", "genshin": "GENSHIN IMPACT",
        "clash of clans": "CLASH OF CLANS", "clash royale": "CLASH ROYALE", "brawl stars": "BRAWL STARS",
        "among us": "AMONG US", "valorant": "VALORANT", "apex legends": "APEX LEGENDS",
        "league of legends": "LEAGUE OF LEGENDS", "lol": "LEAGUE OF LEGENDS", "dota": "DOTA",
        "csgo": "CSGO", "counter strike": "CSGO", "apple": "APPLE", "icloud": "APPLE",
        "samsung": "SAMSUNG", "xiaomi": "XIAOMI", "huawei": "HUAWEI", "oppo": "OPPO",
        "vivo": "VIVO", "oneplus": "ONEPLUS", "realme": "REALME", "nokia": "NOKIA",
        "motorola": "MOTOROLA", "sony": "SONY", "lg": "LG", "amazon": "AMAZON",
        "microsoft": "MICROSOFT", "outlook": "MICROSOFT", "hotmail": "MICROSOFT", "yahoo": "YAHOO",
        "dropbox": "DROPBOX", "spotify": "SPOTIFY", "netflix": "NETFLIX", "zoom": "ZOOM",
        "slack": "SLACK", "trello": "TRELLO", "github": "GITHUB", "gitlab": "GITLAB",
        "bitbucket": "BITBUCKET", "docker": "DOCKER", "paypal": "PAYPAL", "payoneer": "PAYONEER",
        "wise": "WISE", "transferwise": "WISE", "skrill": "SKRILL", "neteller": "NETELLER",
        "binance": "BINANCE", "coinbase": "COINBASE", "blockchain": "BLOCKCHAIN", "bkash": "BKASH",
        "nagad": "NAGAD", "rocket": "ROCKET", "upay": "UPAY", "visa": "VISA", "mastercard": "MASTERCARD",
        "stripe": "STRIPE", "uber": "UBER", "pathao": "PATHAO", "foodpanda": "FOODPANDA",
        "hungrynaki": "HUNGRYNAKI", "daraz": "DARAZ", "aliexpress": "ALIEXPRESS", "ebay": "EBAY",
        "shopify": "SHOPIFY", "airbnb": "AIRBNB", "booking.com": "BOOKING", "booking": "BOOKING",
        "agoda": "AGODA", "expedia": "EXPEDIA", "tinder": "TINDER", "badoo": "BADOO",
        "bumble": "BUMBLE", "happn": "HAPPN", "duolingo": "DUOLINGO", "canva": "CANVA",
        "adobe": "ADOBE", "wordpress": "WORDPRESS", "wix": "WIX", "godaddy": "GODADDY",
        "namecheap": "NAMECHEAP", "cloudflare": "CLOUDFLARE", "digitalocean": "DIGITALOCEAN",
        "heroku": "HEROKU", "firebase": "FIREBASE", "aws": "AWS", "azure": "AZURE",
    }
    
    for keyword, service_name in sorted(service_keywords.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in sms_lower:
            return service_name
    
    return "SMS SERVICE"

# ==================== KEYBOARDS SECTION ====================

def main_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📞 GET NUMBER", style="success"), KeyboardButton("🎯 CUSTOM RANGE", style="primary")],
        [KeyboardButton("💰 BALANCE", style="success"), KeyboardButton("👥 REFER & EARN", style="primary")],
        [KeyboardButton("🏆 LEADERBOARD", style="primary"), KeyboardButton("💬 SUPPORT", style="success")]
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton("⚙️ ADMIN PANEL ⚙️", style="danger")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_keyboard():
    keyboard = [[KeyboardButton("❌ CANCEL", style="danger")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== ADMIN PANEL KEYBOARD ====================

def admin_main_keyboard():
    keyboard = [
        [KeyboardButton("⚙️ SYSTEM CONFIG", style="primary"), KeyboardButton("👥 USER & BALANCE", style="primary")],
        [KeyboardButton("🔐 SECURITY & JOIN", style="primary"), KeyboardButton("📢 NOTICE & B-CAST", style="primary")],
        [KeyboardButton("🔌 API & MONITOR", style="primary"), KeyboardButton("🔙 BACK TO MAIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_system_config_keyboard():
    keyboard = [
        [KeyboardButton("⚙️ SET MAX NUMBERS LIMIT", style="primary"), KeyboardButton("💳 SET WITHDRAW LIMITS", style="primary")],
        [KeyboardButton("💰 SET OTP BONUS", style="primary"), KeyboardButton("👥 SET REFER BONUS", style="primary")],
        [KeyboardButton("📱 SET NUMBERS PER REQUEST", style="primary"), KeyboardButton("⚡ SET COOLDOWN", style="primary")],
        [KeyboardButton("🔧 TOGGLE MAINTENANCE", style="danger"), KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_user_balance_keyboard():
    keyboard = [
        [KeyboardButton("💰 ADD BALANCE", style="primary"), KeyboardButton("➖ REMOVE BALANCE", style="primary")],
        [KeyboardButton("💬 DIRECT MSG USER", style="primary"), KeyboardButton("🔍 SEARCH BY USERNAME", style="primary")],
        [KeyboardButton("👤 USER STATUS CHECK", style="primary"), KeyboardButton("🆔 ALL USER ID", style="primary")],
        [KeyboardButton("💰 ALL USER BALANCE", style="primary"), KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_security_join_keyboard():
    keyboard = [
        [KeyboardButton("🔐 SET FORCE JOIN", style="primary"), KeyboardButton("🔄 TOGGLE FORCE JOIN", style="primary")],
        [KeyboardButton("⛔ BAN USER", style="danger"), KeyboardButton("🔓 UNBAN USER", style="success")],
        [KeyboardButton("📜 BAN USER LIST", style="primary"), KeyboardButton("🔔 TOGGLE JOIN ALERT", style="primary")],
        [KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_notice_bcast_keyboard():
    keyboard = [
        [KeyboardButton("📢 BROADCAST NOTICE", style="primary"), KeyboardButton("🔗 B-CAST WITH BUTTON", style="primary")],
        [KeyboardButton("📝 EDIT LINKS & TEXTS", style="primary"), KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_api_monitor_keyboard():
    keyboard = [
        [KeyboardButton("🔑 CHANGE API KEY", style="success"), KeyboardButton("🌐 CHANGE BASE URL", style="success")],
        [KeyboardButton("🚑 DB COMPACTOR", style="primary"), KeyboardButton("📊 SYS LIVE HEALTH", style="primary")],
        [KeyboardButton("📱 ACTIVE NUMBERS", style="primary"), KeyboardButton("💸 PENDING WITHDRAWALS", style="primary")],
        [KeyboardButton("📋 VIEW CONFIG OVERVIEW", style="success"), KeyboardButton("🛑 DISCONNECT MONITOR", style="danger")],
        [KeyboardButton("🏆 RESET LEADERBOARD", style="danger"), KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ওয়ান-ক্লিক কপি এবং নতুন বাটন টেক্সটের জন্য মেনু লিস্ট আপডেট
MENU_BUTTONS = {
    "📞 GET NUMBER", "🎯 CUSTOM RANGE", "🏆 LEADERBOARD", "💬 SUPPORT", "⚙️ ADMIN PANEL ⚙️", "💰 BALANCE", "👥 REFER & EARN",
    "🔙 BACK TO MAIN", "🔙 BACK TO ADMIN", "❌ CANCEL", "💰 ADD BALANCE", "➖ REMOVE BALANCE", 
    "⚙️ SET MAX NUMBERS LIMIT", "📝 EDIT LINKS & TEXTS", "⛔ BAN USER", "🔓 UNBAN USER",
    "📜 BAN USER LIST", "📢 SEND MESSAGE TO ALL USERS", "🆔 ALL USER ID", "💰 ALL USER BALANCE",
    "💳 SET WITHDRAW LIMITS", "🔧 TOGGLE MAINTENANCE", "🔄 RESET DAILY LIMITS", "🔑 CHANGE API KEY", 
    "🌐 CHANGE BASE URL", "🧹 CLEAR RANGES CACHE", "💾 EXPORT DATABASE", "🧹 CLEAN INACTIVE USERS", 
    "🏥 SYSTEM HEALTH CHECK", "📱 ACTIVE NUMBERS", "💸 PENDING WITHDRAWALS", "📋 VIEW CONFIG OVERVIEW", 
    "🔗 B-CAST WITH BUTTON", "💬 DIRECT MSG USER", "🔍 SEARCH BY USERNAME", "🔐 SET FORCE JOIN", 
    "🔄 TOGGLE FORCE JOIN", "🚑 DB COMPACTOR", "📊 SYS LIVE HEALTH", "⚡ SET COOLDOWN", "📢 BROADCAST NOTICE",
    "🏆 RESET LEADERBOARD", "🛑 DISCONNECT MONITOR", "💰 SET OTP BONUS", "👥 SET REFER BONUS", "📱 SET NUMBERS PER REQUEST",
    "⚙️ SYSTEM CONFIG", "👥 USER & BALANCE", "🔐 SECURITY & JOIN", "📢 NOTICE & B-CAST", "🔌 API & MONITOR", "🔔 TOGGLE JOIN ALERT"
}

# ==================== HELPER FUNCTIONS SECTION ====================

def format_balance(balance):
    return f"{balance:.4f}"

# আল্ট্রা-ডায়নামিক অত্যন্ত শক্তিশালী ওটিপি ফিল্টারিং লজিক (যা N/A প্রবলেমকে পুরোপুরি দূর করবে)
def extract_otp(text):
    if not text or text == "No Content": 
        return "N/A"
    
    text = str(text).strip()
    
    # ১. পুরো মেসেজ যদি নিজেই কেবল একটি ৩ থেকে ৮ ডিজিটের কোড হয়
    clean_digits = re.sub(r'\D', '', text)
    if len(text) <= 10 and text.isdigit() and 3 <= len(text) <= 8:
        return text

    # ২. G-123456 বা g-12345 ফরম্যাটের ওটিপি ডিটেকশন
    g_match = re.search(r'\b[Gg]-(\d{4,8})\b', text)
    if g_match:
        return g_match.group(1)

    # ৩. :স্পেস বা ড্যাশ সহ ওটিপি (যেমন: 123 456 বা 123-456)
    spaced_otp = re.search(r'\b(\d{3})[\s-]?(\d{3})\b', text)
    if spaced_otp:
        return spaced_otp.group(1) + spaced_otp.group(2)

    # ৪. ৩ থেকে ৮ ডিজিটের সাধারণ কোড ডিটেকশন (ওয়ার্ড বাউন্ডারিসহ)
    match_4_8 = re.search(r'\b(\d{4,8})\b', text)
    if match_4_8:
        return match_4_8.group(1)
        
    match_3 = re.search(r'\b(\d{3})\b', text)
    if match_3:
        return match_3.group(1)

    # ৫. ফলব্যাক ম্যাচ (যদি word boundary মিস হয়ে যায়, যেমন code:123456 বা VerificationCode1234)
    fallback_match = re.search(r'(\d{4,8})', text)
    if fallback_match:
        return fallback_match.group(1)
        
    fallback_match_3 = re.search(r'(\d{3})', text)
    if fallback_match_3:
        return fallback_match_3.group(1)

    return "N/A"

def normalize_number(num):
    return re.sub(r'\D', '', str(num))

# মাইনো মাস্কিং স্টাইল (2289✧MINO✧9921)
def mask_number(num):
    num_str = str(num).replace('+', '').replace(' ', '').strip()
    if len(num_str) >= 8:
        return f"{num_str[:4]}✧MINO✧{num_str[-4:]}"
    elif len(num_str) > 4:
        half = len(num_str) // 2
        return f"{num_str[:half]}✧MINO✧{num_str[half:]}"
    return num_str

def format_otp_display(otp):
    otp = str(otp).strip()
    if otp.isdigit() and len(otp) == 6:
        return f"{otp[:3]}-{otp[3:]}"
    return otp

def get_date_reset_time():
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day, 0, 0, 0)
    return today_midnight

def is_valid_bangladesh_number(number):
    number = re.sub(r'\D', '', str(number))
    return len(number) == 11 and number.startswith('01')

def is_range_request(param):
    if 'X' in param.upper():
        return True
    return False

# ==================== DATABASE FUNCTIONS SECTION ====================

def load_data(filename=USER_DATA_FILE):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data, filename=USER_DATA_FILE):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def get_user(uid, username=None, full_name=None):
    uid = str(uid)
    data = load_data()
    if uid not in data:
        data[uid] = {
            "user_id": uid, 
            "balance": 0.0, 
            "total_numbers": 0, 
            "username": username, 
            "full_name": full_name,
            "referrals": 0,
            "referral_earnings": 0.0,
            "referred_by": None
        }
        save_data(data)
    else:
        updated = False
        if "referrals" not in data[uid]:
            data[uid]["referrals"] = 0
            updated = True
        if "referral_earnings" not in data[uid]:
            data[uid]["referral_earnings"] = 0.0
            updated = True
        if "referred_by" not in data[uid]:
            data[uid]["referred_by"] = None
            updated = True
        if username: 
            data[uid]["username"] = username
            updated = True
        if full_name: 
            data[uid]["full_name"] = full_name
            updated = True
        if updated:
            save_data(data)
    return data[uid]

async def update_db_balance(uid, amount):
    uid = str(uid)
    data = load_data()
    if uid in data:
        data[uid]["balance"] = round(data[uid].get("balance", 0.0) + amount, 4)
        save_data(data)
        return data[uid]["balance"]
    return 0.0

def get_all_users():
    data = load_data(USER_DATA_FILE)
    return list(data.keys()) if data else []

def user_exists(uid):
    data = load_data(USER_DATA_FILE)
    return str(uid) in data

# ==================== STATS FUNCTIONS SECTION ====================

def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def add_number_taken(uid, count=1):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    now = datetime.now().isoformat()
    for _ in range(count):
        stats[uid]["numbers_taken"].append(now)
    log_global_activity(uid, "NUMBER_TAKEN", {"count": count})
    save_stats(stats)

def add_otp_received(uid):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    now = datetime.now().isoformat()
    stats[uid]["otps_received"].append(now)
    save_stats(stats)

def get_user_stats(uid):
    uid = str(uid)
    stats = load_stats()
    user_stats = stats.get(uid, {"numbers_taken": [], "otps_received": []})
    
    now = datetime.now()
    today_midnight = get_date_reset_time()
    
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    numbers_taken = user_stats.get("numbers_taken", [])
    otps_received = user_stats.get("otps_received", [])
    
    today_numbers = sum(1 for t in numbers_taken if datetime.fromisoformat(t) >= today_midnight)
    today_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) >= today_midnight)
    
    last24h_numbers = sum(1 for t in numbers_taken if datetime.fromisoformat(t) > last_24h)
    last24h_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) > last_24h)
    
    last7d_numbers = sum(1 for t in numbers_taken if datetime.fromisoformat(t) > last_7d)
    last7d_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) > last_7d)
    
    total_numbers = len(numbers_taken)
    total_otps = len(otps_received)
    
    return {
        "total_numbers": total_numbers,
        "total_otps": total_otps,
        "today_numbers": today_numbers,
        "today_otps": today_otps,
        "last24h_numbers": last24h_numbers,
        "last24h_otps": last24h_otps,
        "last7d_numbers": last7d_numbers,
        "last7d_otps": last7d_otps
    }

def log_global_activity(uid, action, details):
    if not os.path.exists(ACTIVITY_LOGS_FILE):
        with open(ACTIVITY_LOGS_FILE, "w") as f:
            json.dump([], f)
    try:
        with open(ACTIVITY_LOGS_FILE, "r") as f:
            logs = json.load(f)
    except:
        logs = []
    now = datetime.now()
    log_entry = {
        "uid": str(uid),
        "action": action,
        "details": details,
        "timestamp": now.isoformat(),
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S")
    }
    logs.append(log_entry)
    with open(ACTIVITY_LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def get_global_system_stats():
    stats = load_stats()
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day)
    last_7d = now - timedelta(days=7)
    total_n, total_o = 0, 0
    today_n, today_o = 0, 0
    seven_n, seven_o = 0, 0
    for uid in stats:
        u_stats = stats[uid]
        n_list = u_stats.get("numbers_taken", [])
        o_list = u_stats.get("otps_received", [])
        total_n += len(n_list)
        total_o += len(o_list)
        for t in n_list:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight: today_n += 1
            if dt >= last_7d: seven_n += 1
        for t in o_list:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight: today_o += 1
            if dt >= last_7d: seven_o += 1
    return today_n, today_o, seven_n, seven_o, total_n, total_o

# ==================== FASTXOTP API - ACTIVE RANGES FLOW ====================

async def fetch_top55_ranges_by_app():
    ranges_list = None
    api_key, base_url = get_api_credentials()
    for attempt in range(2):
        try:
            r = await client_async.get(
                f"{base_url}/api/liveaccess",
                headers={"X-API-Key": api_key},
                timeout=httpx.Timeout(connect=4.0, read=10.0, write=4.0, pool=4.0)
            )
            data = r.json()
            if data.get("status") == "ok":
                ranges_list = data.get("services", [])
                break
        except Exception:
            if attempt == 0:
                await asyncio.sleep(0.3)

    if ranges_list is None:
        return None, "Server unreachable. Please try again."

    if not ranges_list:
        return {}, None

    top_ranges_by_app = {}
    
    # অনুমোদিত নির্দিষ্ট সার্ভিসগুলোর সেট (বাকিগুলো ব্লক করা হবে)
    allowed_services = {"Facebook", "WhatsApp", "Instagram", "PayPal", "Telegram", "TikTok", "Discord"}

    for svc_obj in ranges_list:
        primary_raw = svc_obj.get("sid", "Unknown App")
        primary_app = get_clean_app_name(primary_raw)
        ranges = svc_obj.get("ranges", [])
        
        if not primary_app or not ranges:
            continue
            
        # নির্দিষ্ট ৭টি সার্ভিস ছাড়া বাকি সব ব্লক করার লজিক
        if primary_app not in allowed_services:
            continue

        icon = get_platform_icon(primary_app)

        if primary_app not in top_ranges_by_app:
            top_ranges_by_app[primary_app] = {"icon": icon, "ranges": [], "total_otps": 0}
        top_ranges_by_app[primary_app]["ranges"].extend(ranges)
        top_ranges_by_app[primary_app]["total_otps"] += len(ranges)

    top_ranges_by_app = dict(
        sorted(top_ranges_by_app.items(),
               key=lambda x: len(x[1]["ranges"]), reverse=True)
    )

    return top_ranges_by_app, None


def build_app_buttons_from_cache(top_ranges_by_app):
    buttons = []
    row = []
    for app_name, info in top_ranges_by_app.items():
        bold_name = make_bold_text(app_name)
        label = f"{bold_name}"
        row.append(InlineKeyboardButton(label, callback_data=f"sel_app_{app_name}", style="primary"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


async def show_app_selection(update, context):
    import time as _time
    uid = update.effective_user.id
    if is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@NETBOLDNETMAIR0")
        await update.message.reply_text(f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if is_under_maintenance(uid):
        await update.message.reply_text("🚧 **SYSTEM UNDER MAINTENANCE** 🚧\n\nSorry, the bot is currently undergoing maintenance. Please try again later.", parse_mode="Markdown")
        return

    # ইউজার ফোর্স জয়েন ভ্যালিডেশন চেক
    is_joined = await is_user_joined_force_channels(uid, context)
    if not is_joined:
        await update.message.reply_text(
            "📢 <b>আপনাকে অবশ্যই আমাদের চ্যানেলগুলোতে জয়েন করতে হবে!</b>\n\nনিচের বোতামগুলো ব্যবহার করে জয়েন করুন এবং চেক বাটনে ক্লিক করুন।",
            parse_mode="HTML",
            reply_markup=build_force_join_keyboard()
        )
        return

    context.user_data.pop("top_ranges_by_app", None)

    cache_age = _time.monotonic() - _ranges_cache["updated_at"]
    if _ranges_cache["data"] and cache_age < 300:
        top_ranges_by_app = _ranges_cache["data"]
        context.user_data["top_ranges_by_app"] = top_ranges_by_app
        buttons = build_app_buttons_from_cache(top_ranges_by_app)
        keyboard = InlineKeyboardMarkup(buttons)
        msg = (
            f"📞 <b>SELECT APP TO GET NUMBER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
        return

    status = await update.message.reply_text("⚡ Loading ranges...")

    top_ranges_by_app, err = await fetch_top55_ranges_by_app()

    if err or not top_ranges_by_app:
        top_ranges_by_app, err = await fetch_top55_ranges_by_app()

    if err:
        await status.edit_text(
            f"❌ <b>Could not load ranges.</b>\n\n"
            f"<blockquote>⚠️ {err}\n\nPlease try again in a moment.</blockquote>",
            parse_mode="HTML"
        )
        return

    if not top_ranges_by_app:
        await status.edit_text("⚠️ No ranges available right now. Try again shortly.")
        return

    _ranges_cache["data"] = top_ranges_by_app
    _ranges_cache["updated_at"] = _time.monotonic()
    context.user_data["top_ranges_by_app"] = top_ranges_by_app

    buttons = build_app_buttons_from_cache(top_ranges_by_app)
    keyboard = InlineKeyboardMarkup(buttons)
    msg = (
        f"📞 <b>SELECT APP TO GET NUMBER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await status.edit_text(msg, parse_mode="HTML", reply_markup=keyboard)

# ==================== CUSTOM RANGE HANDLERS ====================

async def custom_range_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@insotpgrambotowner")
        await update.message.reply_text(f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown")
        return

    if is_under_maintenance(uid):
        await update.message.reply_text("🚧 **SYSTEM UNDER MAINTENANCE** 🚧\n\nSorry, the bot is currently undergoing maintenance. Please try again later.", parse_mode="Markdown")
        return

    is_joined = await is_user_joined_force_channels(uid, context)
    if not is_joined:
        await update.message.reply_text(
            "📢 <b>আপনাকে অবশ্যই আমাদের চ্যানেলগুলোতে জয়েন করতে হবে!</b>\n\nনিচের বোতামগুলো ব্যবহার করে জয়েন করুন এবং চেক বাটনে ক্লিক করুন।",
            parse_mode="HTML",
            reply_markup=build_force_join_keyboard()
        )
        return

    context.user_data["mode"] = "input_custom_range"
    msg = (
        f"🎯 <b>CUSTOM RANGE SYSTEM</b> 🎯\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✍️ <b>অনুগ্রহ করে আপনার কাঙ্ক্ষিত কাস্টম রেঞ্জটি টাইপ করে পাঠান।</b>\n"
        f"<blockquote>💡 উদাহরণ: <code>2290X</code> বা আপনার এপিআই সাপোর্টেড নির্দিষ্ট রেঞ্জ কোড।</blockquote>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=cancel_keyboard())

# ==================== LEADERBOARD CONTROLLER ====================

async def show_leaderboard_command(update, context):
    stats = load_stats()
    sorted_users = []
    for u_id, u_stats in stats.items():
        otp_count = len(u_stats.get("otps_received", []))
        if otp_count > 0:
            sorted_users.append((u_id, otp_count))
    
    sorted_users = sorted(sorted_users, key=lambda x: x[1], reverse=True)[:10]
    
    lines = ["🏆 <b>OTP LEADERBOARD (TOP USERS)</b> 🏆\n━━━━━━━━━━━━━━━━━━━━━━\n"]
    if sorted_users:
        for idx, (user_id, count) in enumerate(sorted_users, 1):
            users_db = load_data(USER_DATA_FILE)
            u_info = users_db.get(str(user_id), {})
            name = u_info.get("full_name") or u_info.get("username") or f"User ({user_id[-4:]})"
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "✨"
            lines.append(f"<b>{medal} {idx}.</b> {html.escape(name)} ➜ <code>{count} OTPs</code>")
    else:
        lines.append("<i>No OTPs received yet. Take numbers and secure the chart!</i>")
    
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

# ==================== SUPPORT CONTROLLER ====================

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = load_settings()
    support_user = settings.get("support_username", "@insotpgrambotowner")
    support_text = "💬 <b>SUPPORT & HELP CENTER</b> 🎧\n\nCLICK THE BUTTON BELOW TO CONTACT SUPPORT 📩"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 SUPPORT", url=f"https://t.me/{support_user.replace('@', '')}", style="primary")],
        [InlineKeyboardButton("👨‍💻 DEVELOPER", url="https://t.me/insotpgrambotowner", style="primary")]
    ])
    await update.message.reply_text(support_text, reply_markup=keyboard, parse_mode="HTML")

# ==================== AUTO OTP MONITOR SECTION ====================

async def monitor_loop(app):
    while True:
        try:
            api_key, base_url = get_api_credentials()
            r = await client_async.get(f"{base_url}/api/otps", headers={"X-API-Key": api_key})
            res = r.json()
            if "data" in res and "otps" in res["data"]:
                otps = res["data"]["otps"]
                paid_data = load_data(PAID_SMS_FILE)
                range_db = load_data(DATA_RANGE_FILE)
                
                paid_keys_set = set(paid_data.keys())
                processed_in_session = set()

                for otp in otps:
                    num = normalize_number(otp.get("number", ""))
                    
                    # N/A প্রবলেম দূরীকরণে ফার্স্ট-প্রায়োরিটি রুটিন চেক
                    raw_otp = otp.get('otp')
                    if raw_otp and str(raw_otp).strip().isdigit() and 3 <= len(str(raw_otp).strip()) <= 8:
                        otp_code = str(raw_otp).strip()
                        full_sms = otp.get('message') or otp.get('sms') or f"OTP: {otp_code}"
                    else:
                        full_sms = otp.get('message') or otp.get('sms') or otp.get('otp') or "No SMS Content"
                        otp_code = extract_otp(full_sms)
                        
                    otp_id = str(otp.get("otp_id") or otp.get("nid") or "")
                    
                    # মাল্টি-ওটিপি সাপোর্ট করার জন্য ইউনিক এসএমএস কি জেনারেশন
                    sms_key = f"{num}_{otp_id}" if otp_id else f"{num}_{full_sms}"

                    if (num in active_numbers and 
                        sms_key not in paid_keys_set and 
                        sms_key not in processed_in_session):
                        
                        details = active_numbers[num]
                        
                        paid_keys_set.add(sms_key)
                        processed_in_session.add(sms_key)
                        paid_data[sms_key] = {"uid": details["uid"], "otp": otp_code}
                        
                        add_otp_received(details["uid"])
                        log_global_activity(details["uid"], "OTP_RECEIVED", {"number": num, "otp": otp_code, "sms": full_sms})

                        # ওটিপি পাওয়ার পর বোনাস ক্রেডিটিং মেকানিজম (0.0020$)
                        settings = load_settings()
                        otp_reward = settings.get("otp_reward", 0.0020)
                        await update_db_balance(details["uid"], otp_reward)

                        country_flag, country_name = get_country_info(num)
                        service_name = detect_service(full_sms)
                        
                        clean_num = num.replace('+', '').strip()
                        masked_number = mask_number(clean_num)
                        full_number = f"+{clean_num}"
                        
                        formatted_otp = format_otp_display(otp_code)
                        service_display = get_clean_app_name(service_name)
                        country_abbr = get_country_abbr(country_name)
                        country_lang = get_country_lang(country_name)
                        
                        # ওয়ান-ক্লিক কপি টেক্সট বাটন জেনারেশন (স্ক্রিনশটের মতো ঢাল আইকনসহ)
                        otp_btn_text = f"{formatted_otp}"
                        if HAS_COPY_BTN:
                            try:
                                btn_copy = InlineKeyboardButton(
                                    text=otp_btn_text,
                                    copy_text=CopyTextButton(text=otp_code)
                                )
                            except Exception:
                                btn_copy = InlineKeyboardButton(text=otp_btn_text, callback_data=f"copy_text_{otp_code}")
                        else:
                            btn_copy = InlineKeyboardButton(text=otp_btn_text, callback_data=f"copy_text_{otp_code}")
                        
                        # ==================== ১. ইউজার ইনবক্স মেসেজ (২য় ছবি অনুযায়ী একদম পরিচ্ছন্ন ডিজাইন) ====================
                        user_otp_msg = f"📞 <code>{full_number}</code>"
                        
                        # ৩য় ছবি অনুযায়ী ইনবক্সের মেসেজে চ্যানেল এবং প্যানেল বাটন আর দেখানো হবে না
                        user_otp_keyboard = InlineKeyboardMarkup([
                            [btn_copy]
                        ])
                        
                        # ==================== ২. ফরওয়ার্ড গ্রুপ মেসেজ (৩য় ছবি অনুযায়ী ফুল NEXO ZONE থিম) ====================
                        group_msg = (
                            f"<blockquote>{country_flag} <b>#{service_display}</b></blockquote>\n\n"
                            f"  📞 <code>{masked_number}</code>\n"
                        )
                        
                        # ৩য় ছবি অনুযায়ী চ্যানেল এবং প্যানেল বাটন শুধুমাত্র ওটিপি গ্রুপে দেখানো হবে
                        group_buttons = InlineKeyboardMarkup([
                            [btn_copy],
                            [
                                InlineKeyboardButton("🤖 Panel ↗", url="https://t.me/Zenex_Number_bot?start=7940416120"),
                                InlineKeyboardButton("📢 Channel ↗", url=settings.get("channel_url", "https://t.me/MinoXofficial0"))
                            ]
                        ])
                        
                        try:
                            await app.bot.send_message(details["uid"], user_otp_msg, parse_mode="HTML", reply_markup=user_otp_keyboard)
                        except Exception as e:
                            print(f"❌ User Message Send Fail: {e}")
                        
                        try:
                            await app.bot.send_message(OTP_GROUP_ID, group_msg, parse_mode="HTML", reply_markup=group_buttons)
                        except Exception as e:
                            print(f"❌ Group Send Fail: {e}")
                        
                        save_data(paid_data, PAID_SMS_FILE)

                current_time = datetime.now()
                expired_nums = []
                for num_key in list(active_numbers.keys()):
                    if hasattr(active_numbers[num_key], 'timestamp'):
                        if (current_time - active_numbers[num_key]['timestamp']).seconds > 3600:
                            expired_nums.append(num_key)
                    else:
                        active_numbers[num_key]['timestamp'] = current_time
                
                for num in expired_nums:
                    del active_numbers[num]
                    
        except Exception as e:
            print(f"Monitor Error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# ==================== WORKER & API SECTION ====================

async def fetch_number_async(range_str):
    try:
        api_key, base_url = get_api_credentials()
        r = await client_async.post(
            f"{base_url}/api/getnum",
            json={"range": range_str, "is_national": False},
            headers={"X-API-Key": api_key}
        )
        data = r.json()
        if "data" in data:
            ndata = data["data"]
            return ndata.get("full_number") or ndata.get("copy") or ndata.get("number")
    except Exception as e: 
        print(f"Fetch number error: {e}")
    return None

async def worker():
    while True:
        task = await request_queue.get()
        try:
            if task['type'] == 'process_numbers':
                await process_numbers(task['update'], task['context'], task['range_text'], task['count'], task.get('edit_message'))
            elif task['type'] == 'auto_number':
                await process_auto_number(task['update'], task['context'], task['range_text'])
        except Exception as e:
            print(f"Worker Error: {e}")
        finally:
            request_queue.task_done()

# ==================== AUTO NUMBER FROM LINK SECTION ====================

async def process_auto_number(update, context, range_text):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@insotpgrambotowner")
        await context.bot.send_message(chat_id=chat_id, text=f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if is_under_maintenance(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚧 **SYSTEM UNDER MAINTENANCE** 🚧\n\nSorry, the bot is currently undergoing maintenance. Please try again later.", parse_mode="Markdown")
        return

    is_joined = await is_user_joined_force_channels(uid, context)
    if not is_joined:
        await context.bot.send_message(
            chat_id=chat_id,
            text="📢 <b>আপনাকে অবশ্যই আমাদের চ্যানেলগুলোতে জয়েন করতে হবে!</b>",
            parse_mode="HTML",
            reply_markup=build_force_join_keyboard()
        )
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING...")

    try:
        result = await fetch_number_async(range_text)
        generated_num = normalize_number(result) if result else None
        
        if not generated_num:
            await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")
            return
        
        add_number_taken(uid, 1)
        last_range[uid] = range_text
        active_numbers[generated_num] = {"uid": uid, "range": range_text}
        save_number_range_info(uid, generated_num, range_text)
        
        country_flag, country_name = get_country_info(generated_num)
        
        assign_text = (
            f"☑️ {country_flag} {country_name} Number selected\n"
            f"🌀 Waiting for OTP..."
        )
        
        settings = load_settings()
        otp_group_url = settings.get("otp_group_url", "https://t.me/+31eV11IT7WQzMjI9")
        channel_url = settings.get("channel_url", "https://t.me/MinoXofficial0")
        
        # ট্যাপ-টু-কপি বাটন তৈরি এবং চারপাশের অতিরিক্ত ইমোজি দূরীকরণ
        if HAS_COPY_BTN:
            num_btn = InlineKeyboardButton(text=f"+{generated_num}", copy_text=CopyTextButton(text=f"+{generated_num}"))
        else:
            num_btn = InlineKeyboardButton(text=f"+{generated_num}", callback_data=f"copy_text_{generated_num}")
            
        keyboard = [
            [num_btn],
            [InlineKeyboardButton("🔵🟢 Change Number", callback_data="same_range", style="danger")],
            [InlineKeyboardButton("🌐 Change Country", callback_data="back_to_apps", style="success")],
            [InlineKeyboardButton("🔒 Otp Group", url=otp_group_url, style="primary")],
            [InlineKeyboardButton("🔗 Main Channel", url=channel_url, style="primary")]
        ]
        
        await status_msg.edit_text(assign_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        print(f"Auto Number Error: {e}")
        await status_msg.edit_text(f"❌ Error occurred: {str(e)}")

# ==================== USER PANEL SECTION ====================

async def process_numbers(update, context, range_text, count, edit_message=None):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@NETBOLDNETMAIR0")
        await context.bot.send_message(chat_id=chat_id, text=f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if is_under_maintenance(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚧 **SYSTEM UNDER MAINTENANCE** 🚧\n\nSorry, the bot is currently undergoing maintenance. Please try again later.", parse_mode="Markdown")
        return

    is_joined = await is_user_joined_force_channels(uid, context)
    if not is_joined:
        await context.bot.send_message(
            chat_id=chat_id,
            text="📢 <b>আপনাকে অবশ্যই আমাদের চ্যানেলগুলোতে জয়েন করতে হবে!</b>",
            parse_mode="HTML",
            reply_markup=build_force_join_keyboard()
        )
        return

    if not edit_message:
        status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING . . .")  
    else:
        status_msg = edit_message

    try:
        add_number_taken(uid, count)
        last_range[uid] = range_text   

        tasks = [fetch_number_async(range_text) for _ in range(count)]  
        results = await asyncio.gather(*tasks)  
        generated_nums = [normalize_number(n) for n in results if n]  

        if not generated_nums:  
            err_text = "❌ NO NUMBERS FOUND. TRY A VALID RANGE."
            await status_msg.edit_text(err_text)
            return  

        for clean_num in generated_nums:  
            active_numbers[clean_num] = {"uid": uid, "range": range_text}
            save_number_range_info(uid, clean_num, range_text)

        country_flag, country_name = get_country_info(generated_nums[0])
        
        assign_text = (
            f"☑️ {country_flag} {country_name} Number selected\n"
            f"🌀 Waiting for OTP..."
        )

        settings = load_settings()
        otp_group_url = settings.get("otp_group_url", "https://t.me/+31eV11IT7WQzMjI9")
        channel_url = settings.get("channel_url", "https://t.me/MinoXofficial0")

        keyboard = []
        for g_num in generated_nums:
            # ট্যাপ-টু-কপি বাটন তৈরি এবং চারপাশের অতিরিক্ত ইমোজি দূরীকরণ
            if HAS_COPY_BTN:
                btn = InlineKeyboardButton(text=f"+{g_num}", copy_text=CopyTextButton(text=f"+{g_num}"))
            else:
                btn = InlineKeyboardButton(text=f"+{g_num}", callback_data=f"copy_text_{g_num}")
            keyboard.append([btn])
            
        keyboard.extend([
            [InlineKeyboardButton("🔵🟢 Change Number", callback_data="same_range", style="danger")],
            [InlineKeyboardButton("🌐 Change Country", callback_data="back_to_apps", style="success")],
            [InlineKeyboardButton("🔒 Otp Group", url=otp_group_url, style="primary")],
            [InlineKeyboardButton("🔗 Main Channel", url=channel_url, style="primary")]
        ])

        await status_msg.edit_text(assign_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        print(f"Process Number Error: {e}")
        await status_msg.edit_text(f"❌ System Error: {str(e)}")

# ==================== WITHDRAW FUNCTIONS (UPDATED TO $) ====================

async def withdraw_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        context.user_data["withdraw_method"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠", reply_markup=main_keyboard(uid))
        return
    
    try:
        amount = float(text)
    except:
        await update.message.reply_text("⚠️ PLEASE SEND A VALID AMOUNT!", reply_markup=cancel_keyboard())
        return
    
    balance = get_user(uid)['balance']
    min_w, max_w = get_withdraw_limits()
    
    if amount < min_w or amount > max_w:
        await update.message.reply_text(f"📉 MINIMUM WITHDRAW {min_w}$ \n\n📈 MAX WITHDRAWAL {max_w}$", reply_markup=cancel_keyboard())
        return
    
    if amount > balance:
        await update.message.reply_text("🚫 YOU DO NOT HAVE ENOUGH BALANCE !", reply_markup=cancel_keyboard())
        return
    
    context.user_data["withdraw_amount"] = amount
    context.user_data["withdraw_mode"] = "number"
    msg = (
        f"📞 PLEASE SEND YOUR ACCOUNT NUMBER !\n\n"
        f"<blockquote>🔢 EXAMPLE: 17XXXXXXXX</blockquote>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=cancel_keyboard())

async def withdraw_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        context.user_data["withdraw_method"] = None
        context.user_data["withdraw_amount"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠", reply_markup=main_keyboard(uid))
        return
    
    method = context.user_data.get("withdraw_method")
    amount = context.user_data.get("withdraw_amount")
    payment_number = text
    payment_id = generate_payment_id()
    
    user_payment_msg = (
        "✨ <b>YOUR PAYMENT DETAILS!</b> ✨\n\n"
        f"<blockquote>📝 PAYMENT METHOD: {method}\n"
        f"📞 YOUR PAYMENT NUMBER: {payment_number}\n\n"
        f"✅ IF PAYMENT DETAILS ARE CORRECT, CLICK THE CONFIRM BUTTON\n"
        f"❌ OR IF PAYMENT DETAILS ARE WRONG, CLICK THE CANCEL BUTTON</blockquote>"
    )
    
    confirm_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ CANCEL", callback_data="withdraw_cancel", style="danger"),
            InlineKeyboardButton("✅ CONFIRM", callback_data="withdraw_confirm", style="success")
        ]
    ])
    
    context.user_data["temp_withdraw"] = {
        "method": method,
        "amount": amount,
        "number": payment_number,
        "payment_id": payment_id
    }
    
    await update.message.reply_text(
        user_payment_msg,
        parse_mode="HTML",
        reply_markup=confirm_keyboard
    )

async def process_withdraw_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    temp_data = context.user_data.get("temp_withdraw")
    if not temp_data:
        await query.message.reply_text("⚠️ SESSION EXPIRED. PLEASE TRY AGAIN.", reply_markup=main_keyboard(uid))
        return
    
    method = temp_data["method"]
    amount = temp_data["amount"]
    payment_number = temp_data["number"]
    payment_id = temp_data["payment_id"]
    
    new_balance = await update_db_balance(uid, -amount)
    
    withdraw_requests = load_withdraw_requests()
    withdraw_requests[str(payment_id)] = {
        "user_id": uid,
        "method": method,
        "amount": amount,
        "number": payment_number,
        "payment_id": payment_id,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    save_withdraw_requests(withdraw_requests)
    
    user_confirm_msg = (
        f"✅ <b>WITHDRAWAL REQUEST SUBMITTED</b> ✅\n\n"
        f"<blockquote>💰 আপনার উইথড্র রিকোয়েস্টটি এডমিনের কাছে পাঠানো হয়েছে।\n"
        f"⏳ অনুগ্রহ করে এডমিন এপ্রুভ করা পর্যন্ত অপেক্ষা করুন।</blockquote>\n\n"
        f"<blockquote>✨ WITHDRAW DETAILS:\n"
        f"📝 METHOD: <code>{method}</code>\n"
        f"📞 NUMBER: <code>{payment_number}</code>\n"
        f"💰 AMOUNT: <code>{format_balance(amount)}$</code>\n"
        f"🆔 PAYMENT ID: <code>{payment_id}</code></blockquote>"
    )
    await query.message.edit_text(user_confirm_msg, parse_mode="HTML")

    success_back_msg = (
        "🎉 <b>WITHDRAW REQUEST SUBMIT SUCCESSFUL</b> 🎉\n\n"
        "🏠 <b>BACK TO MENU</b> 🏠"
    )
    await context.bot.send_message(
        chat_id=uid,
        text=success_back_msg,
        parse_mode="HTML",
        reply_markup=main_keyboard(uid)
    )

    admin_msg = (
        f"✅ <b>NEW WITHDRAWAL REQUEST RECEIVED</b> ✅\n\n"
        f"<blockquote>🆔 USER ID : <code>{uid}</code>\n"
        f"✨ YOUR PAYMENT DETAILS!\n"
        f"📝 PAYMENT METHOD: <code>{method}</code>\n"
        f"📞 YOUR PAYMENT NUMBER: <code>{payment_number}</code>\n"
        f"🆔 PAYMENT ID : <code>{payment_id}</code></blockquote>\n\n"
        f"<blockquote>💰 AMOUNT: <code>{format_balance(amount)}$</code></blockquote>"
    )
    
    admin_decision_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ CANCEL", callback_data=f"admin_reject_{payment_id}", style="danger"),
            InlineKeyboardButton("✅ CONFIRM", callback_data=f"admin_approve_{payment_id}", style="success")
        ]
    ])
    
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                admin_id, 
                admin_msg, 
                parse_mode="HTML", 
                reply_markup=admin_decision_keyboard
            )
        except Exception as e:
            print(f"Failed to send to admin {admin_id}: {e}")
    
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None
    context.user_data["withdraw_method"] = None
    context.user_data["withdraw_amount"] = None

async def process_withdraw_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None
    context.user_data["withdraw_method"] = None
    context.user_data["withdraw_amount"] = None
    
    await query.message.edit_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠")
    await context.bot.send_message(uid, "🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))

# ==================== ADMIN PANEL - WITHDRAW APPROVAL ====================

async def admin_approve_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    query = update.callback_query
    await query.answer()
    
    withdraw_requests = load_withdraw_requests()
    if payment_id not in withdraw_requests:
        await query.message.reply_text("⚠️ WITHDRAW REQUEST NOT FOUND!")
        return
    
    request_data = withdraw_requests[payment_id]
    uid = request_data["user_id"]
    method = request_data["method"]
    amount = request_data["amount"]
    payment_number = request_data["number"]
    
    withdraw_requests[payment_id]["status"] = "approved"
    save_withdraw_requests(withdraw_requests)
    
    user_final_msg = (
        "🎉 <b>WITHDRAWAL SUCCESSFUL</b> 🎉\n\n"
        "<blockquote>💰 আপনার উইথড্র রিকোয়েস্টটি এডমিন এপ্রুভ করেছে এবং পেমেন্ট সফলভাবে পাঠানো হয়েছে !</blockquote>\n\n"
        "<blockquote>📱 WHAT TO DO NEXT:\n"
        "📥 আপনি যেই মেথড এবং নাম্বারে উইথড্র দিয়েছিলেন, অনুগ্রহ করে সেই নাম্বারটি চেক করুন।\n"
        "⏳ আশা করা যায় আপনার অ্যাকাউন্টে টাকা চলে গিয়েছে।\n"
        "⚠️ NOTE: যদি কোনো কারণে পেমেন্ট না পেয়ে থাকেন, তাহলে দ্রুত আমাদের Support Team-এর সাথে যোগাযোগ করুন।</blockquote>\n\n"
        "<blockquote>✨ ধন্যবাদ আমাদের সাথে থাকার জন্য! ✨\n"
        "🚀 FAST X OTP Number bot | SECURE & TRUSTED ⚡</blockquote>\n\n"
        f"<blockquote>✨ YOUR PAYMENT DETAILS:\n"
        f"📝 PAYMENT METHOD: <code>{method}</code>\n"
        f"📞 PAYMENT NUMBER: <code>{payment_number}</code>\n"
        f"💰 AMOUNT: <code>{format_balance(amount)}$</code>\n"
        f"🆔 PAYMENT ID: <code>{payment_id}</code></blockquote>"
    )
    
    try:
        await context.bot.send_message(uid, user_final_msg, parse_mode="HTML")
    except:
        pass
    
    await query.message.edit_text(
        f"✅ **WITHDRAW REQUEST CONFIRMED SUCCESSFULLY** ✅\n\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"👤 User ID: `{uid}`\n"
        f"💰 Amount: `{format_balance(amount)}$`\n\n"
        f"🎉 Payment has been approved and user has been notified!",
        parse_mode="Markdown"
    )

async def admin_reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    query = update.callback_query
    await query.answer()
    
    withdraw_requests = load_withdraw_requests()
    if payment_id not in withdraw_requests:
        await query.message.reply_text("⚠️ WITHDRAW REQUEST NOT FOUND!")
        return
    
    request_data = withdraw_requests[payment_id]
    uid = request_data["user_id"]
    method = request_data["method"]
    amount = request_data["amount"]
    payment_number = request_data["number"]
    
    withdraw_requests[payment_id]["status"] = "rejected"
    save_withdraw_requests(withdraw_requests)
    
    # ব্যালেন্স ফেরত দেওয়া যদি রিজেক্ট করা হয়
    await update_db_balance(uid, amount)
    
    user_reject_msg = (
        "❌ **WITHDRAWAL REQUEST REJECTED** ❌\n\n"
        "⚠️ SORRY, THE ADMIN HAS NOT APPROVED AND PAID YOUR WITHDRAWAL REQUEST.\n\n"
        "🛑 **REASON:** > YOUR WITHDRAW REQUEST HAS BEEN CANCELLED AND AMOUNT HAS BEEN REFUNDED TO YOUR BALANCE.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **WITHDRAW DETAILS:**\n"
        f"📝 METHOD: `{method}`\n"
        f"📞 NUMBER: `{payment_number}`\n"
        f"💰 AMOUNT: `{format_balance(amount)}$`\n"
        f"🆔 ID: `{payment_id}`"
    )
    
    try:
        await context.bot.send_message(uid, user_reject_msg, parse_mode="Markdown")
    except:
        pass
    
    await query.message.edit_text(
        f"❌ **WITHDRAW REQUEST CANCELLED & REFUNDED** ❌\n\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"👤 User ID: `{uid}`\n"
        f"💰 Amount: `{format_balance(amount)}$`\n\n"
        f"🔴 This payment has been rejected and user has been notified!",
        parse_mode="Markdown"
    )

# ==================== ADMIN PANEL - BALANCE MANAGEMENT ====================

async def admin_add_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_balance_mode"] = True
    context.user_data["remove_balance_mode"] = False
    await update.message.reply_text("💰 **SEND USER ID TO ADD BALANCE FOR USER!** 💰\n\n📝 PLEASE SEND THE TELEGRAM USER ID:", parse_mode="Markdown")

async def admin_remove_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["remove_balance_mode"] = True
    context.user_data["add_balance_mode"] = False
    await update.message.reply_text("💸 **SEND USER ID TO REMOVE BALANCE FROM USER!** 💸\n\n📝 PLEASE SEND THE TELEGRAM USER ID:", parse_mode="Markdown")

async def process_add_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_add = update.message.text.strip()
    
    if not uid_to_add.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! PLEASE SEND A VALID NUMERIC TELEGRAM ID.")
        return
    
    uid_to_add_int = int(uid_to_add)
    
    if not user_exists(uid_to_add_int):
        await update.message.reply_text("❌ USER NOT FOUND! THIS USER HAS NEVER STARTED THE BOT.")
        context.user_data["add_balance_mode"] = False
        return
    
    context.user_data["pending_add_user"] = uid_to_add_int
    await update.message.reply_text("💵 **SEND AMOUNT TO ADD BALANCE:**\n\n💰 ENTER AMOUNT IN $:", parse_mode="Markdown")

async def process_remove_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_remove = update.message.text.strip()
    
    if not uid_to_remove.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! PLEASE SEND A VALID NUMERIC TELEGRAM ID.")
        return
    
    uid_to_remove_int = int(uid_to_remove)
    
    if not user_exists(uid_to_remove_int):
        await update.message.reply_text("❌ USER NOT FOUND! THIS USER HAS NEVER STARTED THE BOT.")
        context.user_data["remove_balance_mode"] = False
        return
    
    context.user_data["pending_remove_user"] = uid_to_remove_int
    await update.message.reply_text("💸 **SEND AMOUNT TO REMOVE BALANCE:**\n\n💰 ENTER AMOUNT IN $:", parse_mode="Markdown")

async def process_add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A POSITIVE NUMBER.")
            return
    except:
        await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A VALID NUMBER.")
        return
    
    uid = context.user_data.get("pending_add_user")
    if not uid:
        context.user_data["add_balance_mode"] = False
        await update.message.reply_text("⚠️ SESSION EXPIRED. PLEASE TRY AGAIN.")
        return
    
    user_data = get_user(uid)
    old_balance = user_data.get("balance", 0)
    new_balance = await update_db_balance(uid, amount)
    
    admin_msg = (
        "✅ **ADD BALANCE SUCCESSFUL** ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 USER ID : `{uid}`\n"
        f"💰 ADD BALANCE AMOUNT : `{format_balance(amount)}$`\n"
        f"📊 PREVIOUS BALANCE : `{format_balance(old_balance)}$`\n"
        f"📈 NEW BALANCE : `{format_balance(new_balance)}$`\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 COPY USER ID", callback_data=f"copy_id_{uid}")]
    ])
    
    await update.message.reply_text(admin_msg, parse_mode="Markdown", reply_markup=admin_keyboard)
    
    user_msg = (
        "🎉 **THE ADMIN HAS ADDED MONEY TO YOUR ACCOUNT** 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **AMOUNT OF MONEY :** `{format_balance(amount)}$`\n"
        f"📊 **YOUR NEW BALANCE :** `{format_balance(new_balance)}$`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💫 THANK YOU FOR USING OUR SERVICE!"
    )
    
    try:
        await context.bot.send_message(uid, user_msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ COULD NOT NOTIFY USER. BUT BALANCE ADDED SUCCESSFULLY.")
    
    context.user_data["add_balance_mode"] = False
    context.user_data["pending_add_user"] = None

async def process_remove_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A POSITIVE NUMBER.")
            return
    except:
        await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A VALID NUMBER.")
        return
    
    uid = context.user_data.get("pending_remove_user")
    if not uid:
        context.user_data["remove_balance_mode"] = False
        await update.message.reply_text("⚠️ SESSION EXPIRED. PLEASE TRY AGAIN.")
        return
    
    user_data = get_user(uid)
    old_balance = user_data.get("balance", 0)
    
    if amount > old_balance:
        error_msg = (
            "❌ **INSUFFICIENT BALANCE!** ❌\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 USER ID : `{uid}`\n"
            f"💰 CURRENT BALANCE : `{format_balance(old_balance)}$`\n"
            f"💸 REQUESTED REMOVE : `{format_balance(amount)}$`\n\n"
            "⚠️ **PLEASE SEND A VALID REMOVE BALANCE AMOUNT!**\n"
            "⚠️ AMOUNT CANNOT EXCEED CURRENT BALANCE!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(error_msg, parse_mode="Markdown")
        context.user_data["remove_balance_mode"] = False
        context.user_data["pending_remove_user"] = None
        return
    
    new_balance = await update_db_balance(uid, -amount)
    
    admin_msg = (
        "✅ **REMOVE BALANCE SUCCESSFUL** ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 USER ID : `{uid}`\n"
        f"💸 REMOVE BALANCE AMOUNT : `{format_balance(amount)}$`\n"
        f"📊 PREVIOUS BALANCE : `{format_balance(old_balance)}$`\n"
        f"📉 NEW BALANCE : `{format_balance(new_balance)}$`\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 COPY USER ID", callback_data=f"copy_id_{uid}")]
    ])
    
    await update.message.reply_text(admin_msg, parse_mode="Markdown", reply_markup=admin_keyboard)
    
    user_msg = (
        "⚠️ **ADMIN HAS REMוVED MONEY FROM YOUR ACCOUNT** ⚠️\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💸 **AMOUNT REMOVED :** `{format_balance(amount)}$`\n"
        f"📊 **YOUR NEW BALANCE :** `{format_balance(new_balance)}$`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📞 CONTACT SUPPORT IF YOU HAVE ANY QUESTIONS!"
    )
    
    try:
        await context.bot.send_message(uid, user_msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ COULD NOT NOTIFY USER. BUT BALANCE REMOVED SUCCESSFULLY.")
    
    context.user_data["remove_balance_mode"] = False
    context.user_data["pending_remove_user"] = None

# ==================== ADMIN PANEL - BAN/UNBAN ====================

async def admin_ban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_ban_mode"] = True
    context.user_data["admin_unban_mode"] = False
    await update.message.reply_text("🚫 SENT TELEGRAM ID TO BAN USER 🚫\n\n📝 Please send the Telegram User ID you want to ban:")

async def admin_unban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_unban_mode"] = True
    context.user_data["admin_ban_mode"] = False
    await update.message.reply_text("🔓 SENT UNBAN USER ID 🔓\n\n📝 Please send the Telegram User ID you want to unban:")

async def process_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_ban = update.message.text.strip()
    
    if not uid_to_ban.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! Please send a valid numeric Telegram ID.")
        return
    
    uid_to_ban_int = int(uid_to_ban)
    
    if not user_exists(uid_to_ban_int):
        await update.message.reply_text("❌ THIS USER NOT FOUND FOR YOUR TELEGRAM BOT ❌\n\n⚠️ This user has never started the bot or doesn't exist in our database.")
        context.user_data["admin_ban_mode"] = False
        return
    
    if is_user_banned(uid_to_ban_int):
        await update.message.reply_text("⚠️ USER IS ALREADY BANNED ⚠️\n\nThis user has already been banned from the bot.")
        context.user_data["admin_ban_mode"] = False
        return
    
    ban_user(uid_to_ban_int)
    
    try:
        await context.bot.send_message(
            uid_to_ban_int,
            "🚫 **YOU HAVE BEEN BANNED** 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n"
            "📞 CONTACT SUPPORT FOR MORE INFORMATION.\n\n"
            "💬 SUPPORT: @NETBOLDNETMAIR0",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ USER BAN SUCCESSFUL ✅\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚫 Banned User ID: `{uid_to_ban}`\n"
        f"📊 Status: User can no longer use any bot features.\n\n"
        f"🔓 To unban this user, use the UNBAN USER option.",
        parse_mode="Markdown",
        reply_markup=admin_security_join_keyboard()
    )
    context.user_data["admin_ban_mode"] = False

async def process_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_unban = update.message.text.strip()
    
    if not uid_to_unban.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! Please send a valid numeric Telegram ID.")
        return
    
    uid_to_unban_int = int(uid_to_unban)
    
    if not is_user_banned(uid_to_unban_int):
        await update.message.reply_text("⚠️ THIS USER IS NOT BANNED ⚠️\n\n📝 Please send a banned user ID to unban.")
        context.user_data["admin_unban_mode"] = False
        return
    
    unban_user(uid_to_unban_int)
    
    try:
        await context.bot.send_message(
            uid_to_unban_int,
            "✅ **YOU HAVE BEEN UNBANNED** ✅\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎉 CONGRATULATIONS! YOU HAVE BEEN UNBANNED.\n"
            "✨ YOU CAN NOW USE ALL BOT FEATURES AGAIN.\n\n"
            "📞 USE /start TO BEGIN USING THE BOT.",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ USER UNBAN SUCCESSFUL ✅\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔓 Unbanned User ID: `{uid_to_unban}`\n"
        f"📊 Status: User can now use all bot features again.",
        parse_mode="Markdown",
        reply_markup=admin_security_join_keyboard()
    )
    context.user_data["admin_unban_mode"] = False

async def show_banned_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banned_list = load_banned_users()
    
    if not banned_list:
        await update.message.reply_text("📜 **BANNED USER LIST** 📜\n━━━━━━━━━━━━━━━━━━━━\n\n✅ No users are currently banned.", parse_mode="Markdown", reply_markup=admin_security_join_keyboard())
        return
    
    banned_text = "📜 **BANNED USER LIST** 📜\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, uid in enumerate(banned_list, 1):
        banned_text += f"{i}. User ID: `{uid}`\n"
    
    banned_text += f"\n📊 Total Banned Users: {len(banned_list)}"
    
    await update.message.reply_text(banned_text, parse_mode="Markdown", reply_markup=admin_security_join_keyboard())

# ==================== ADMIN DYNAMIC SETTERS ====================

async def admin_set_max_numbers_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    context.user_data["admin_edit_mode"] = "max_limit"
    await update.message.reply_text(
        "⚙️ <b>SET MAX NUMBERS LIMIT (BATCH BATCH)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<blockquote>👤 প্রতিটি ইউজার একসাথে সর্বোচ্চ কতটি নাম্বার তুলতে পারবেন তা সংখ্যায় টাইপ করে পাঠান:</blockquote>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )

async def admin_set_cooldown_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    context.user_data["admin_edit_mode"] = "cooldown"
    await update.message.reply_text(
        "⚡ <b>SET COOLDOWN TIME</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<blockquote>⏱️ নম্বর রিকোয়েস্ট/চেঞ্জিং এর কুলডাউন সেকেন্ড সংখ্যায় পাঠান (যেমন: 4.0):</blockquote>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )

async def admin_set_force_join_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    context.user_data["admin_edit_mode"] = "force_join_channels"
    settings = load_settings()
    current_ch = ", ".join(settings.get("force_join_channels", []))
    await update.message.reply_text(
        "🔐 <b>SET FORCE JOIN CHANNELS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<blockquote>Current Channels: <code>{current_ch}</code></blockquote>\n\n"
        "<blockquote>নতুন চ্যানেল লিস্ট টাইপ করে পাঠান (কমা ব্যবহার করে একাধিক চ্যানেল দিন, যেমন: @chan1, @chan2):</blockquote>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )

async def admin_edit_links_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Edit Welcome Msg", callback_data="edit_txt_welcome", style="primary")],
        [InlineKeyboardButton("🔗 Edit OTP Group Link", callback_data="edit_txt_otpgroup", style="primary")],
        [InlineKeyboardButton("📢 Edit Channel Link", callback_data="edit_txt_channel", style="primary")],
        [InlineKeyboardButton("💬 Edit Support Username", callback_data="edit_txt_support", style="primary")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back_to_config", style="danger")]
    ])
    
    await update.message.reply_text(
        "📝 <b>EDIT LINKS & TEXTS SYSTEM</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "নিচের বাটনগুলো থেকে সিলেক্ট করুন আপনি কোন লেখা বা লিঙ্ক পরিবর্তন করতে চান:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# ==================== MESSAGE HANDLER SECTION ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    text = update.message.text.strip()

    # Dynamic State Clearance on Keyboard Button Clicks
    if text in MENU_BUTTONS:
        context.user_data.pop("withdraw_mode", None)
        context.user_data.pop("withdraw_method", None)
        context.user_data.pop("withdraw_amount", None)
        context.user_data.pop("admin_edit_mode", None)
        context.user_data.pop("add_balance_mode", None)
        context.user_data.pop("pending_add_user", None)
        context.user_data.pop("remove_balance_mode", None)
        context.user_data.pop("pending_remove_user", None)
        context.user_data.pop("admin_ban_mode", None)
        context.user_data.pop("admin_unban_mode", None)
        context.user_data.pop("mode", None)
        context.user_data.pop("broadcast_mode", None)

    if context.user_data.get("withdraw_mode") == "amount":
        await withdraw_amount_received(update, context)
        return
    
    if context.user_data.get("withdraw_mode") == "number":
        await withdraw_number_received(update, context)
        return

    # Admin Editing Processing
    edit_mode = context.user_data.get("admin_edit_mode")
    if edit_mode and is_admin(uid):
        context.user_data["admin_edit_mode"] = None
        settings = load_settings()
        
        if edit_mode == "welcome":
            settings["welcome_message"] = text
            await update.message.reply_text("✅ Welcome Message সফলভাবে আপডেট করা হয়েছে!", reply_markup=admin_notice_bcast_keyboard())
            save_settings(settings)
        elif edit_mode == "otpgroup":
            if text.startswith("http"):
                settings["otp_group_url"] = text
                await update.message.reply_text("✅ OTP Group লিঙ্ক সফলভাবে আপডেট করা হয়েছে!", reply_markup=admin_notice_bcast_keyboard())
                save_settings(settings)
            else:
                await update.message.reply_text("❌ ভুল লিঙ্ক ফরম্যাট! অবশ্যই https:// থাকতে হবে।", reply_markup=admin_notice_bcast_keyboard())
        elif edit_mode == "channel":
            if text.startswith("http"):
                settings["channel_url"] = text
                await update.message.reply_text("✅ Channel লিঙ্ক সফলভাবে আপডেট করা হয়েছে!", reply_markup=admin_notice_bcast_keyboard())
                save_settings(settings)
            else:
                await update.message.reply_text("❌ ভুল লিঙ্ক ফরম্যাট! অবশ্যই https:// থাকতে হবে।", reply_markup=admin_notice_bcast_keyboard())
        elif edit_mode == "support":
            if text.startswith("@"):
                settings["support_username"] = text
                await update.message.reply_text("✅ Support Username সফলভাবে আপডেট করা হয়েছে!", reply_markup=admin_notice_bcast_keyboard())
                save_settings(settings)
            else:
                await update.message.reply_text("❌ ভুল ইউজারনেম ফরম্যাট! অবশ্যই @ থাকতে হবে।", reply_markup=admin_notice_bcast_keyboard())
        elif edit_mode == "max_limit":
            if text.isdigit():
                settings["max_numbers_per_user"] = int(text)
                await update.message.reply_text(f"✅ আজকের পর থেকে প্রতিটি ইউজার একসাথে সর্বোচ্চ {text} টি নাম্বার তুলতে পারবেন (Batch Generation)!", reply_markup=admin_system_config_keyboard())
                save_settings(settings)
            else:
                await update.message.reply_text("❌ ভুল ইনপুট! অনুগ্রহ করে শুধুমাত্র একটি সংখ্যা টাইপ করে পাঠান।", reply_markup=admin_system_config_keyboard())
        elif edit_mode == "cooldown":
            try:
                settings["cooldown_time"] = float(text)
                await update.message.reply_text(f"✅ Cooldown লিমিট সফলভাবে {text} সেকেন্ড সেট করা হয়েছে!", reply_markup=admin_system_config_keyboard())
                save_settings(settings)
            except:
                await update.message.reply_text("❌ ভুল ইনপুট! সংখ্যা টাইপ করুন।", reply_markup=admin_system_config_keyboard())
        elif edit_mode == "force_join_channels":
            channels_list = [ch.strip() for ch in text.split(",") if ch.strip()]
            settings["force_join_channels"] = channels_list
            await update.message.reply_text(f"✅ Force Join চ্যানেলসমূহ সফলভাবে সেট করা হয়েছে!", reply_markup=admin_security_join_keyboard())
            save_settings(settings)
        
        # New admin_edit_mode handlers
        elif edit_mode == "otp_bonus":
            try:
                val = float(text)
                settings["otp_reward"] = val
                await update.message.reply_text(f"✅ OTP Reward সফলভাবে {val}$ সেট করা হয়েছে!", reply_markup=admin_system_config_keyboard())
                save_settings(settings)
            except:
                await update.message.reply_text("❌ ভুল ইনপুট! অনুগ্রহ করে সঠিক দশমিক সংখ্যা পাঠান।", reply_markup=admin_system_config_keyboard())
        elif edit_mode == "refer_bonus":
            try:
                val = float(text)
                settings["refer_bonus"] = val
                await update.message.reply_text(f"✅ Referral Bonus সফলভাবে {val}$ সেট করা হয়েছে!", reply_markup=admin_system_config_keyboard())
                save_settings(settings)
            except:
                await update.message.reply_text("❌ ভুল ইনপুট! অনুগ্রহ করে সঠিক দশমিক সংখ্যা পাঠান।", reply_markup=admin_system_config_keyboard())
        elif edit_mode == "numbers_per_request":
            try:
                val = int(text)
                if val < 1: raise ValueError
                settings["numbers_per_request"] = val
                await update.message.reply_text(f"✅ Numbers Per Request সফলভাবে {val} টি সেট করা হয়েছে!", reply_markup=admin_system_config_keyboard())
                save_settings(settings)
            except:
                await update.message.reply_text("❌ ভুল ইনপুট! অনুগ্রহ করে ধনাত্মক পূর্ণসংখ্যা টাইপ করুন (যেমন: 1 বা 2)।", reply_markup=admin_system_config_keyboard())
        elif edit_mode == "api_key":
            settings["api_key"] = text
            await update.message.reply_text("✅ API Key সফলভাবে আপডেট করা হয়েছে!", reply_markup=admin_api_monitor_keyboard())
            save_settings(settings)
        elif edit_mode == "base_url":
            if text.startswith("http"):
                settings["base_url"] = text
                await update.message.reply_text("✅ BASE URL সফলভাবে আপডেট করা হয়েছে!", reply_markup=admin_api_monitor_keyboard())
                save_settings(settings)
            else:
                await update.message.reply_text("❌ ভুল ইউআরএল ফরম্যাট! অবশ্যই http:// বা https:// থাকতে হবে।", reply_markup=admin_api_monitor_keyboard())
        elif edit_mode == "withdraw_limits":
            parts = text.split()
            if len(parts) == 2:
                try:
                    settings["min_withdraw"] = float(parts[0])
                    settings["max_withdraw"] = float(parts[1])
                    await update.message.reply_text(f"✅ Withdraw Limits সফলভাবে আপডেট করা হয়েছে: Minimum {parts[0]}$ , Maximum {parts[1]}$", reply_markup=admin_system_config_keyboard())
                    save_settings(settings)
                except:
                    await update.message.reply_text("❌ ভুল ফরম্যাট! অনুগ্রহ করে সঠিক সংখ্যা প্রদান করুন।", reply_markup=admin_system_config_keyboard())
            else:
                await update.message.reply_text("❌ ভুল ফরম্যাট! উদাহরণ: `0.5 100` এভাবে টাইপ করে পাঠান।", parse_mode="Markdown", reply_markup=admin_system_config_keyboard())
        elif edit_mode == "direct_msg_uid":
            if text.isdigit():
                context.user_data["admin_direct_uid"] = text
                context.user_data["admin_edit_mode"] = "direct_msg_text"
                await update.message.reply_text("💬 **Now enter the message content to send:**", parse_mode="Markdown", reply_markup=cancel_keyboard())
            else:
                await update.message.reply_text("❌ Invalid User ID! Please send numeric Telegram ID.", reply_markup=admin_user_balance_keyboard())
        elif edit_mode == "direct_msg_text":
            target_uid = context.user_data.get("admin_direct_uid")
            try:
                await context.bot.send_message(chat_id=int(target_uid), text=f"💬 **MESSAGE FROM ADMIN:**\n\n{text}", parse_mode="Markdown")
                await update.message.reply_text("✅ Message sent successfully!", reply_markup=admin_user_balance_keyboard())
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to send message: {e}", reply_markup=admin_user_balance_keyboard())
        elif edit_mode == "search_username":
            uname = text.replace("@", "").strip().lower()
            users = load_data(USER_DATA_FILE)
            found = False
            for u_id, details in users.items():
                if str(details.get("username", "")).lower() == uname:
                    found = True
                    stats = get_user_stats(u_id)
                    status_msg = (
                        f"👤 **USER FOUND CHECK** 📊\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"🆔 **User ID:** `{u_id}`\n"
                        f"🏷️ **Username:** @{details.get('username')}\n"
                        f"💰 **Balance:** `{details.get('balance', 0.0)}$`\n\n"
                        f"✨ **TODAY STATUS**\n"
                        f"📱 NUMBERS TAKEN : {stats['today_numbers']}\n"
                        f"🔑 OTPS RECEIVED : {stats['today_otps']}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📂 CHECK ALL DATA 📂", callback_data=f"full_logs_{u_id}")]])
                    await update.message.reply_text(status_msg, parse_mode="Markdown", reply_markup=kb)
                    break
            if not found:
                await update.message.reply_text("❌ No user found with that username.", reply_markup=admin_user_balance_keyboard())
        elif edit_mode == "broadcast_btn_msg":
            context.user_data["admin_broadcast_msg"] = text
            context.user_data["admin_edit_mode"] = "broadcast_btn_text"
            await update.message.reply_text("💬 **Enter the Button Text:**", parse_mode="Markdown", reply_markup=cancel_keyboard())
        elif edit_mode == "broadcast_btn_text":
            context.user_data["admin_broadcast_btn_text"] = text
            context.user_data["admin_edit_mode"] = "broadcast_btn_url"
            await update.message.reply_text("🔗 **Enter the Button URL (https://...):**", parse_mode="Markdown", reply_markup=cancel_keyboard())
        elif edit_mode == "broadcast_btn_url":
            if text.startswith("http"):
                msg_content = context.user_data.get("admin_broadcast_msg")
                btn_txt = context.user_data.get("admin_broadcast_btn_text")
                btn_url = text
                
                users = load_data(USER_DATA_FILE)
                success, fail = 0, 0
                kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_txt, url=btn_url)]])
                
                status_msg = await update.message.reply_text("🚀 Broadcasting started...")
                for target_uid in users.keys():
                    try:
                        await context.bot.send_message(chat_id=int(target_uid), text=f"<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>\n\n{msg_content}", parse_mode="HTML", reply_markup=kb)
                        success += 1
                    except:
                        fail += 1
                    await asyncio.sleep(0.05)
                
                await status_msg.delete()
                await update.message.reply_text(f"✅ Broadcast with button completed!\n\nSuccess: `{success}`\nFailed: `{fail}`", parse_mode="Markdown", reply_markup=admin_notice_bcast_keyboard())
            else:
                await update.message.reply_text("❌ Invalid URL! Must start with https://. Please try again.", reply_markup=admin_notice_bcast_keyboard())
        elif edit_mode == "input_custom_range":
            # কাস্টম রেঞ্জ হ্যান্ডলার ট্রিগার
            range_input = text.strip()
            settings = load_settings()
            count = settings.get("numbers_per_request", 1)
            await request_queue.put({
                'type': 'process_numbers', 
                'update': update, 
                'context': context, 
                'range_text': range_input, 
                'count': count
            })
        return

    if context.user_data.get("add_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_add_user"):
            await process_add_balance_amount(update, context)
        else:
            await process_add_balance_user(update, context)
        return
    
    if context.user_data.get("remove_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_remove_user"):
            await process_remove_balance_amount(update, context)
        else:
            await process_remove_balance_user(update, context)
        return

    if context.user_data.get("admin_ban_mode") and is_admin(uid):
        await process_ban_user(update, context)
        return
    
    if context.user_data.get("admin_unban_mode") and is_admin(uid):
        await process_unban_user(update, context)
        return

    if not is_admin(uid) and is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@NETBOLDNETMAIR0")
        await update.message.reply_text(f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if is_under_maintenance(uid):
        await update.message.reply_text("🚧 **SYSTEM UNDER MAINTENANCE** 🚧\n\nSorry, the bot is currently undergoing maintenance. Please try again later.", parse_mode="Markdown")
        return

    if text == "❌ CANCEL":
        context.user_data.clear()
        await update.message.reply_text("❌ CANCELLED", reply_markup=main_keyboard(uid))
        return

    # --- BALANCE BUTTON (GORGEOUS PREMIUM INTERFACE) ---
    if text == "💰 BALANCE":
        user_data = get_user(uid)
        balance = user_data.get("balance", 0.0)
        min_w, max_w = get_withdraw_limits()
        
        balance_msg = (
            f"💳 <b>MY WALLET & BALANCE</b> 💳\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<blockquote>💵 <b>Current Balance:</b> <code>{balance:.4f}$</code></blockquote>\n"
            f"<blockquote>📉 <b>Minimum Withdraw:</b> <code>{min_w:.2f}$</code></blockquote>\n"
            f"<blockquote>📈 <b>Maximum Withdraw:</b> <code>{max_w:.2f}$</code></blockquote>\n\n"
            f"👇 <b>Select your withdrawal method below:</b>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Bkash", callback_data="withdraw_Bkash"),
                InlineKeyboardButton("Nagad", callback_data="withdraw_Nagad")
            ],
            [
                InlineKeyboardButton("Rocket", callback_data="withdraw_Rocket"),
                InlineKeyboardButton("Binance", callback_data="withdraw_Binance")
            ],
            [
                InlineKeyboardButton("Back to Menu", callback_data="back_to_menu_inline")
            ]
        ])
        await update.message.reply_text(balance_msg, parse_mode="HTML", reply_markup=keyboard)
        return

    # --- REFER & EARN BUTTON (PREMIUM RE-DESIGN) ---
    if text == "👥 REFER & EARN":
        user_data = get_user(uid)
        settings = load_settings()
        refer_bonus = settings.get("refer_bonus", 0.050)
        
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start={uid}"
        
        referrals = user_data.get("referrals", 0)
        referral_earnings = user_data.get("referral_earnings", 0.0)
        balance = user_data.get("balance", 0.0)
        
        refer_msg = (
            f"👥 <b>REFERRAL PROGRAM</b> 👥\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📢 <b>Invite your friends and earn money instantly!</b>\n\n"
            f"🔗 <b>Your Referral Link:</b>\n"
            f"<blockquote><code>{ref_link}</code></blockquote>\n\n"
            f"📊 <b>Referral Stats:</b>\n"
            f"<blockquote>• Total Referrals: <code>{referrals}</code>\n"
            f"• Referral Earnings: <code>{referral_earnings:.4f}$</code>\n"
            f"• Bonus per Referral: <code>{refer_bonus:.4f}$</code></blockquote>\n"
            f"💰 <b>Current Wallet Balance:</b> <code>{balance:.4f}$</code>"
        )
        await update.message.reply_text(refer_msg, parse_mode="HTML")
        return

    # --- ADMIN SUB-CATEGORY REDIRECT OPERATIONS ---

    if text == "⚙️ SYSTEM CONFIG" and is_admin(uid):
        await update.message.reply_text("⚙️ **System Configuration Category:**", parse_mode="Markdown", reply_markup=admin_system_config_keyboard())
        return

    if text == "👥 USER & BALANCE" and is_admin(uid):
        await update.message.reply_text("👥 **User & Balance Category:**", parse_mode="Markdown", reply_markup=admin_user_balance_keyboard())
        return

    if text == "🔐 SECURITY & JOIN" and is_admin(uid):
        await update.message.reply_text("🔐 **Security & Force Join Category:**", parse_mode="Markdown", reply_markup=admin_security_join_keyboard())
        return

    if text == "📢 NOTICE & B-CAST" and is_admin(uid):
        await update.message.reply_text("📢 **Notices & Broadcasting Category:**", parse_mode="Markdown", reply_markup=admin_notice_bcast_keyboard())
        return

    if text == "🔌 API & MONITOR" and is_admin(uid):
        await update.message.reply_text("🔌 **API & Live Monitoring Category:**", parse_mode="Markdown", reply_markup=admin_api_monitor_keyboard())
        return

    # --- MAIN SUB-MENU ACTIONS (MAPPED CORRECTLY WITH ZERO MISMATCH) ---

    if text == "💰 ADD BALANCE" and is_admin(uid):
        await admin_add_balance_start(update, context)
        return

    if text == "➖ REMOVE BALANCE" and is_admin(uid):
        await admin_remove_balance_start(update, context)
        return

    if text == "⚙️ SET MAX NUMBERS LIMIT" and is_admin(uid):
        await admin_set_max_numbers_start(update, context)
        return

    if text == "💳 SET WITHDRAW LIMITS" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "withdraw_limits"
        await update.message.reply_text(
            "💳 <b>SET WITHDRAW LIMITS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<blockquote>উইথড্রর সর্বনিম্ন এবং সর্বোচ্চ সীমা টাইপ করে স্পেস দিয়ে পাঠান (যেমন: 0.5 100.0):</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "🔧 TOGGLE MAINTENANCE" and is_admin(uid):
        settings = load_settings()
        settings["maintenance_mode"] = not settings.get("maintenance_mode", False)
        save_settings(settings)
        status = "ENABLED 🟢" if settings["maintenance_mode"] else "DISABLED 🔴"
        await update.message.reply_text(f"🔧 Maintenance Mode has been {status}!", reply_markup=admin_system_config_keyboard())
        return

    if text == "🔄 RESET DAILY LIMITS" and is_admin(uid):
        stats = load_stats()
        for u_id in stats:
            stats[u_id]["numbers_taken"] = []
            stats[u_id]["otps_received"] = []
        save_stats(stats)
        await update.message.reply_text("🔄 All user daily stats and limits have been reset successfully!", reply_markup=admin_system_config_keyboard())
        return

    if text == "💬 DIRECT MSG USER" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "direct_msg_uid"
        await update.message.reply_text(
            "💬 <b>DIRECT MESSAGE TO USER</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<blockquote>মেসেজ পাঠাতে ইউজারের Telegram ID টাইপ করে পাঠান:</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "🔍 SEARCH BY USERNAME" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "search_username"
        await update.message.reply_text(
            "🔍 <b>SEARCH USER BY USERNAME</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<blockquote>ইউজারের ইউজারনেম টাইপ করে পাঠান (@ ছাড়া বা @ সহ):</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "📝 EDIT LINKS & TEXTS" and is_admin(uid):
        await admin_edit_links_start(update, context)
        return

    if text == "🔐 SET FORCE JOIN" and is_admin(uid):
        await admin_set_force_join_start(update, context)
        return

    if text == "🔄 TOGGLE FORCE JOIN" and is_admin(uid):
        settings = load_settings()
        settings["force_join_enabled"] = not settings.get("force_join_enabled", False)
        save_settings(settings)
        status = "ENABLED 🟢" if settings["force_join_enabled"] else "DISABLED 🔴"
        await update.message.reply_text(f"🔐 Force Join System has been {status}!", reply_markup=admin_security_join_keyboard())
        return

    if text == "🔔 TOGGLE JOIN ALERT" and is_admin(uid):
        settings = load_settings()
        settings["join_alert_enabled"] = not settings.get("join_alert_enabled", True)
        save_settings(settings)
        status = "ENABLED 🟢" if settings["join_alert_enabled"] else "DISABLED 🔴"
        await update.message.reply_text(f"🔔 New User Join Notification is now {status}!", reply_markup=admin_security_join_keyboard())
        return

    if text == "🚑 DB COMPACTOR" and is_admin(uid):
        await optimize_database_system(uid)
        await update.message.reply_text("🚑 Database compaction and memory clean done!", reply_markup=admin_api_monitor_keyboard())
        return

    if text == "📊 SYS LIVE HEALTH" and is_admin(uid):
        start_time = time.monotonic()
        api_status = "Unknown"
        try:
            api_key, base_url = get_api_credentials()
            r = await client_async.get(f"{base_url}/api/liveaccess", headers={"X-API-Key": api_key}, timeout=5.0)
            latency = (time.monotonic() - start_time) * 1000
            api_status = f"🟢 Connected ({latency:.1f}ms)"
        except Exception as e:
            api_status = f"🔴 Offline: {str(e)}"
        
        users_count = len(get_all_users())
        health_report = (
            f"🏥 **SYSTEM LIVE HEALTH REPORT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 **API Status:** {api_status}\n"
            f"?? **Total Registered:** `{users_count}`\n"
            f"📱 **Active Reserved:** `{len(active_numbers)}`"
        )
        await update.message.reply_text(health_report, parse_mode="Markdown", reply_markup=admin_api_monitor_keyboard())
        return

    if text == "⚡ SET COOLDOWN" and is_admin(uid):
        await admin_set_cooldown_start(update, context)
        return

    if text == "💰 SET OTP BONUS" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "otp_bonus"
        await update.message.reply_text(
            "💰 **SET OTP REWARD BONUS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<blockquote>প্রতিটি ওটিপি সফলভাবে আসার পর ইউজার কত ডলার বোনাস পাবে তা টাইপ করে পাঠান (যেমন: 0.0030):</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "👥 SET REFER BONUS" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "refer_bonus"
        await update.message.reply_text(
            "👥 **SET REFERRAL BONUS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<blockquote>প্রতিটি সফল রেফারেলের জন্য ইউজার কত ডলার বোনাস পাবে তা টাইপ করে পাঠান (যেমন: 0.050):</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "📱 SET NUMBERS PER REQUEST" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "numbers_per_request"
        await update.message.reply_text(
            "📱 **SET NUMBERS PER REQUEST (BATCH SIZE)**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<blockquote>ইউজার যখন একটি কান্ট্রি সিলেক্ট করবে, তখন তাকে একসাথে কয়টি নাম্বার দেওয়া হবে তা টাইপ করে পাঠান (যেমন: 1 বা 3):</blockquote>",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "📢 BROADCAST NOTICE" and is_admin(uid):
        context.user_data["broadcast_mode"] = True
        await update.message.reply_text("📢 Send the notice message content to broadcast to all users:", reply_markup=cancel_keyboard())
        return

    if text == "🔗 B-CAST WITH BUTTON" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "broadcast_btn_msg"
        await update.message.reply_text("📢 **Enter the Broadcast Message content:**", parse_mode="Markdown", reply_markup=cancel_keyboard())
        return

    if text == "🏆 RESET LEADERBOARD" and is_admin(uid):
        data = load_data()
        data["leaderboard"] = {"last_reset": time.time(), "stats": {}}
        save_data(data)
        await update.message.reply_text("🏆 **Leaderboard Reset Successful!**", parse_mode="Markdown", reply_markup=admin_api_monitor_keyboard())
        return

    if text == "🛑 DISCONNECT MONITOR" and is_admin(uid):
        active_numbers.clear()
        await update.message.reply_text("🛑 **All active reserved numbers have been disconnected and flushed!**", parse_mode="Markdown", reply_markup=admin_api_monitor_keyboard())
        return

    if text == "🏆 LEADERBOARD":
        await show_leaderboard_command(update, context)
        return

    if text == "💬 SUPPORT":
        await support_command(update, context)
        return

    if text == "📞 GET NUMBER":
        await show_app_selection(update, context)
        return

    # কাস্টম রেঞ্জ বাটন প্রসেস ট্রিগার
    if text == "🎯 CUSTOM RANGE":
        await custom_range_start(update, context)
        return

    # কাস্টম রেঞ্জ ইনপুট সাবমিশন হ্যান্ডলার
    if context.user_data.get("mode") == "input_custom_range":
        range_input = text.strip()
        context.user_data["mode"] = None
        settings = load_settings()
        count = settings.get("numbers_per_request", 1)
        await request_queue.put({
            'type': 'process_numbers', 
            'update': update, 
            'context': context, 
            'range_text': range_input, 
            'count': count
        })
        return

    if context.user_data.get("mode") in ["range_1"]:
        if "X" in text.upper() or text.isdigit():
            count = 1
            context.user_data["mode"] = None
            await request_queue.put({'type': 'process_numbers', 'update': update, 'context': context, 'range_text': text, 'count': count})
        return
    
    # ==================== ADMIN PANEL - MAIN HANDLERS ====================

    if text == "⚙️ ADMIN PANEL ⚙️" and is_admin(uid):
        context.user_data["admin_mode"] = "main"
        admin_welcome = ("⌬━━━━━━━━━━━━━━━━━━━━⌬\n       WELCOME ADMIN PANEL\n⌬━━━━━━━━━━━━━━━━━━━━⌬")
        await update.message.reply_text(admin_welcome, reply_markup=admin_main_keyboard(), parse_mode="Markdown")
        return

    if text == "🔙 BACK TO MAIN" and context.user_data.get("admin_mode"):
        context.user_data.clear()
        await update.message.reply_text("🔙 Back to main menu.", reply_markup=main_keyboard(uid))
        return

    if text == "🔙 BACK TO ADMIN":
        context.user_data.clear()
        context.user_data["admin_mode"] = "main"
        await update.message.reply_text("🔙 Back to admin panel.", reply_markup=admin_main_keyboard())
        return

    if text == "🔑 CHANGE API KEY" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "api_key"
        await update.message.reply_text("🔑 **Enter the new Voltxlite API Key:**", parse_mode="Markdown", reply_markup=cancel_keyboard())
        return

    if text == "🌐 CHANGE BASE URL" and is_admin(uid):
        context.user_data["admin_edit_mode"] = "base_url"
        await update.message.reply_text("🌐 **Enter the new BASE URL:**\nExample: `http://voltxlite.com`", parse_mode="Markdown", reply_markup=cancel_keyboard())
        return

    if text == "🧹 CLEAR RANGES CACHE" and is_admin(uid):
        global _ranges_cache
        _ranges_cache["data"] = None
        _ranges_cache["updated_at"] = 0.0
        await update.message.reply_text("🧹 **Top 55 Ranges cache cleared successfully!**", parse_mode="Markdown", reply_markup=admin_main_keyboard())
        return

    if text == "💾 EXPORT DATABASE" and is_admin(uid):
        files_to_send = [USER_DATA_FILE, SETTINGS_FILE, WITHDRAW_DATA_FILE, STATS_FILE]
        for file_path in files_to_send:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await update.message.reply_document(document=f, caption=f"💾 Backup file: `{file_path}`", parse_mode="Markdown")
        await update.message.reply_text("Base Export completed!", reply_markup=admin_main_keyboard())
        return

    if text == "🧹 CLEAN INACTIVE USERS" and is_admin(uid):
        users = load_data(USER_DATA_FILE)
        inactive = []
        for u, inf in list(users.items()):
            if inf.get("balance", 0.0) == 0.0 and inf.get("total_numbers", 0) == 0:
                inactive.append(u)
                del users[u]
        save_data(users, USER_DATA_FILE)
        await update.message.reply_text(f"🧹 Cleaned `{len(inactive)}` inactive users with 0$ balance and 0 total numbers!", parse_mode="Markdown", reply_markup=admin_main_keyboard())
        return

    if text == "🏥 SYSTEM HEALTH CHECK" and is_admin(uid):
        start_time = time.monotonic()
        api_status = "Unknown"
        try:
            api_key, base_url = get_api_credentials()
            r = await client_async.get(f"{base_url}/api/liveaccess", headers={"X-API-Key": api_key}, timeout=5.0)
            latency = (time.monotonic() - start_time) * 1000
            api_status = f"🟢 Connected ({latency:.1f}ms)"
        except Exception as e:
            api_status = f"🔴 Offline/Error: {str(e)}"
        
        users_count = len(get_all_users())
        banned_count = len(load_banned_users())
        active_numbers_count = len(active_numbers)
        
        health_report = (
            f"🏥 **SYSTEM HEALTH REPORT** 🏥\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 **API Connection:** {api_status}\n"
            f"👥 **Total Registered Users:** `{users_count}`\n"
            f"🚫 **Total Banned Users:** `{banned_count}`\n"
            f"📱 **Active Reserved Numbers:** `{active_numbers_count}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(health_report, parse_mode="Markdown", reply_markup=admin_main_keyboard())
        return

    if text == "📱 ACTIVE NUMBERS" and is_admin(uid):
        active_cnt = len(active_numbers)
        if active_cnt == 0:
            await update.message.reply_text("📱 No phone numbers are currently active/reserved.", reply_markup=admin_main_keyboard())
            return
        
        lines = []
        for num, details in list(active_numbers.items()):
            lines.append(f"📞 +{num} -> User ID: `{details['uid']}` | Range: `{details.get('range', 'N/A')}`")
        
        report = "📱 **ACTIVE RESERVED NUMBERS** 📱\n━━━━━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(lines[:30])
        if active_cnt > 30:
            report += f"\n\n... and {active_cnt - 30} more active numbers."
        await update.message.reply_text(report, parse_mode="Markdown", reply_markup=admin_main_keyboard())
        return

    if text == "💸 PENDING WITHDRAWALS" and is_admin(uid):
        withdraws = load_withdraw_requests()
        pendings = [w for w in withdraws.values() if w.get("status") == "pending"]
        if not pendings:
            await update.message.reply_text("💸 No withdrawal requests are currently pending.", reply_markup=main_keyboard(uid))
            return
        
        lines = []
        for w in pendings:
            lines.append(f"🆔 ID: `{w['payment_id']}` | User: `{w['user_id']}` | Method: `{w['method']}` | Number: `{w['number']}` | Amount: `{w['amount']}$`")
        
        report = "💸 **PENDING WITHDRAWAL REQUESTS** 💸\n━━━━━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(lines[:20])
        await update.message.reply_text(report, parse_mode="Markdown", reply_markup=admin_main_keyboard())
        return

    if text == "📋 VIEW CONFIG OVERVIEW" and is_admin(uid):
        settings = load_settings()
        api_key, base_url = get_api_credentials()
        min_w, max_w = get_withdraw_limits()
        overview = (
            f"📋 **BOT CONFIGURATION OVERVIEW** 📋\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 **API Key:** `{api_key}`\n"
            f"🌐 **BASE URL:** `{base_url}`\n"
            f"🚀 **Max Numbers Per Batch:** `{settings.get('max_numbers_per_user', 100)}`\n"
            f"📱 **Numbers Per Request:** `{settings.get('numbers_per_request', 1)}`\n"
            f"💰 **OTP Bonus:** `{settings.get('otp_reward', 0.0020)}$`\n"
            f"👥 **Refer Bonus:** `{settings.get('refer_bonus', 0.050)}$`\n"
            f"🚧 **Maintenance Mode:** `{'ENABLED' if settings.get('maintenance_mode', False) else 'DISABLED'}`\n"
            f"💳 **Withdraw Limits:** `{min_w}$ - {max_w}$`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(overview, parse_mode="Markdown", reply_markup=admin_main_keyboard())
        return
    
    if text == "👤 USER STATUS CHECK" and is_admin(uid):
        context.user_data["mode"] = "input_user_id"
        msg = (
            "<blockquote>🔍 <b>ENTER TELEGRAM ID</b> 🔍</blockquote>\n\n"
            "<blockquote>💬 PLEASE ENTER THE TELEGRAM ID OF THE USER YOU WANT TO SEARCH FOR :</blockquote>"
        )
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if context.user_data.get("mode") == "input_user_id" and is_admin(uid):
        target_uid = text.strip()
        if not target_uid.isdigit():
            await update.message.reply_text("❌ INVALID ID! PLEASE SEND A NUMERIC TELEGRAM ID.")
            return
        
        context.user_data["mode"] = None
        stats = get_user_stats(target_uid)
        
        status_msg = (
            f"👤 <b>USER STATUS CHECK</b> 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ <b>TODAY ({datetime.now().strftime('%d/%m/%Y')})</b>\n"
            f"📱 NUMBERS TAKEN : {stats['today_numbers']}\n"
            f"🔑 OTPS RECEIVED : {stats['today_otps']} ⚡\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n"
            f"📱 NUMBERS TAKEN : {stats['last7d_numbers']}\n"
            f"🔑 OTPS RECEIVED : {stats['last7d_otps']} 🚀\n\n"
            f"🌐 <b>ALL TIME RECORD</b>\n"
            f"📱 TOTAL NUMBERS : {stats['total_numbers']}\n"
            f"🔑 TOTAL OTPS : {stats['total_otps']} 💎\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 <b>FAST X OTP Number bot | LIVE REAL-TIME DATA</b> ⚡"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 CHECK ALL DATA 📂", callback_data=f"full_logs_{target_uid}")]
        ])
        
        await update.message.reply_text(status_msg, parse_mode="HTML", reply_markup=keyboard)
        return

    if text == "🆔 ALL USER ID" and is_admin(uid):
        users = get_all_users()
        if users:
            total_users = len(users)
            file_lines = []
            for i, user_id in enumerate(users, 1):
                file_lines.append(f"{i}️⃣ {user_id}")
            
            file_content = "\n".join(file_lines)
            file = io.BytesIO(file_content.encode("utf-8"))
            file.name = f"ALL_USERS_{total_users}.txt"
            
            caption = f"📋 **ALL USER LIST** 📋\n\n👥 Total Users: {total_users}"
            await update.message.reply_document(
                document=file,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=admin_user_balance_keyboard()
            )
        else:
            await update.message.reply_text("No users found.", reply_markup=admin_user_balance_keyboard())
        return

    if text == "💰 ALL USER BALANCE" and is_admin(uid):
        user_db = load_data(USER_DATA_FILE)
        if user_db:
            total_users = len(user_db)
            total_system_balance = 0.0
            balance_lines = []
            
            for i, (user_id, info) in enumerate(user_db.items(), 1):
                u_bal = info.get("balance", 0.0)
                total_system_balance += u_bal
                balance_lines.append(f"{i}. ID: {user_id} | Balance: {u_bal:.4f}$")
            
            file_content = "💰 ALL USER BALANCE REPORT 💰\n"
            file_content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            file_content += f"👥 Total Users: {total_users}\n"
            file_content += f"💵 Total System Balance: {total_system_balance:.4f}$\n"
            file_content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            file_content += "\n".join(balance_lines)
            
            file_io = io.BytesIO(file_content.encode("utf-8"))
            file_io.name = f"{total_system_balance:.4f}usd.txt"
            
            report_msg = (
                "💰 <b>ALL USER BALANCE REPORT</b> 💰\n\n"
                f"<blockquote>👥 Total Users: {total_users}</blockquote>\n"
                f"<blockquote>💵 Total System Balance: {total_system_balance:.4f}$ </blockquote>"
            )
            
            await update.message.reply_document(
                document=file_io,
                caption=report_msg,
                parse_mode="HTML",
                reply_markup=admin_user_balance_keyboard()
            )
        else:
            await update.message.reply_text("❌ No user data found.")
        return

    if text == "📜 BAN USER LIST" and is_admin(uid):
        await show_banned_users_list(update, context)
        return

    if text == "⛔ BAN USER" and is_admin(uid):
        await admin_ban_user_start(update, context)
        return

    if text == "🔓 UNBAN USER" and is_admin(uid):
        await admin_unban_user_start(update, context)
        return

    if text == "📢 SEND MESSAGE TO ALL USERS" and is_admin(uid):
        context.user_data["broadcast_mode"] = True
        await update.message.reply_text(
            "📢 <b>ADMIN BROADCAST SYSTEM (PRO)</b>\n\n"
            "💬 আপনি এখন যা পাঠাবেন তা সকল ইউজারের কাছে প্রফেশনাল হেডারসহ চলে যাবে।", 
            parse_mode="HTML", 
            reply_markup=cancel_keyboard()
        )
        return

    if context.user_data.get("broadcast_mode") and is_admin(uid):
        context.user_data["broadcast_mode"] = False
        
        user_db = load_data(USER_DATA_FILE)
        all_uids = list(user_db.keys())
        
        if not all_uids:
            await update.message.reply_text("❌ পাঠানোর জন্য কোনো ইউজার পাওয়া যায়নি!")
            return

        success_ids, fail_ids = [], []
        status_msg = await update.message.reply_text(f"🚀 <b>ব্রডকাস্ট শুরু হয়েছে...</b>\n🎯 টার্গেট: {len(all_uids)} জন ইউজার।", parse_mode="HTML")

        def format_broadcast_msg(text_content):
            if not text_content: return "<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>"
            formatted = re.sub(r'(\d{3,}[xX]{3,})', r'<code>\1</code>', str(text_content))
            return f"<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>\n\n{formatted}"

        for user_id_str in all_uids:
            try:
                target_id = int(user_id_str)
                
                if update.message.text:
                    await context.bot.send_message(chat_id=target_id, text=format_broadcast_msg(update.message.text), parse_mode="HTML")
                else:
                    new_caption = format_broadcast_msg(update.message.caption) if update.message.caption else "<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>"
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=update.message.chat_id,
                        message_id=update.message.message_id,
                        caption=new_caption,
                        parse_mode="HTML"
                    )
                
                success_ids.append(user_id_str)
            except:
                fail_ids.append(user_id_str)
            
            await asyncio.sleep(0.05)

        report_text = (
            f"✅ <b>ADMIN NOTICE COMPLETE !</b>\n\n"
            f"📊 <b>BROADCAST REPORT:</b>\n\n"
            f"<blockquote>✅ SUCCESSFULLY SENT: {len(success_ids)} USERS !</blockquote>\n"
            f"<blockquote>❌ FAILED TO SEND: {len(fail_ids)} USERS !</blockquote>"
        )
        
        await status_msg.delete()
        await context.bot.send_message(chat_id=uid, text=report_text, parse_mode="HTML", reply_markup=main_keyboard(uid))

        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if success_ids:
            s_file = io.BytesIO(("\n".join(success_ids)).encode()); s_file.name = f"SUCCESS_{random_suffix}.txt"
            await context.bot.send_document(chat_id=uid, document=s_file, caption="✅ Success User List")
        if fail_ids:
            f_file = io.BytesIO(("\n".join(fail_ids)).encode()); f_file.name = f"FAILED_{random_suffix}.txt"
            await context.bot.send_document(chat_id=uid, document=f_file, caption="❌ Failed User List")
        
        return

    else:
        await update.message.reply_text("🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))

# ==================== COMMAND HANDLERS SECTION ====================

async def get1number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@NETBOLDNETMAIR0")
        await update.message.reply_text(f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return
    await show_app_selection(update, context)

# ==================== START & CALLBACK SECTION ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uid_str = str(uid)
    username = update.effective_user.username
    full_name = update.effective_user.full_name
    
    existing_data = load_data(USER_DATA_FILE)
    is_new_user = uid_str not in existing_data
    
    get_user(uid, username, full_name)
    
    # নতুন মেম্বার জয়েন নোটিফিকেশন অ্যালার্ট
    if is_new_user:
        settings = load_settings()
        if settings.get("join_alert_enabled", True):
            alert_msg = (
                f"🔔 <b>NEW USER JOINED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
                f"🏷️ <b>Name:</b> {html.escape(full_name or 'N/A')}\n"
                f"👤 <b>Username:</b> @{username if username else 'N/A'}"
            )
            for admin_id in ADMINS:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=alert_msg, parse_mode="HTML")
                except:
                    pass
    
    args = context.args
    if args:
        param = args[0]
        
        if is_range_request(param):
            range_text = param
            await request_queue.put({
                'type': 'auto_number', 
                'update': update, 
                'context': context, 
                'range_text': range_text
            })
            return
        
        # রেফারেল রিকোয়েস্ট ভ্যালিডেশন
        elif param.isdigit() and is_new_user:
            referrer_id = str(param)
            if referrer_id != uid_str and referrer_id in existing_data:
                user_data = get_user(uid)
                user_data["referred_by"] = referrer_id
                existing_data[uid_str] = user_data
                save_data(existing_data, USER_DATA_FILE)
                
                settings = load_settings()
                refer_bonus = settings.get("refer_bonus", 0.050)
                
                referrer_data = existing_data[referrer_id]
                referrer_data["balance"] = round(referrer_data.get("balance", 0.0) + refer_bonus, 4)
                referrer_data["referrals"] = referrer_data.get("referrals", 0) + 1
                referrer_data["referral_earnings"] = round(referrer_data.get("referral_earnings", 0.0) + refer_bonus, 4)
                
                existing_data[referrer_id] = referrer_data
                save_data(existing_data, USER_DATA_FILE)
                
                try:
                    ref_fullname = full_name or "N/A"
                    ref_uname = username if username else "N/A"
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=(
                            f"👥 <b>New Referral Successful!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"👤 User: {html.escape(ref_fullname)} (@{ref_uname})\n"
                            f"💰 Bonus Credited: <code>+{refer_bonus}$</code>"
                        ),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Failed to notify referrer: {e}")
    
    context.user_data.clear()
    
    settings = load_settings()
    start_msg = settings.get("welcome_message", WELCOME_MESSAGE)
    
    await update.message.reply_text(start_msg, parse_mode="HTML")
    await update.message.reply_text("🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()
    
    if not is_admin(uid) and is_user_banned(uid):
        settings = load_settings()
        support = settings.get("support_username", "@NETBOLDNETMAIR0")
        await query.edit_message_text(f"🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT: {support}", parse_mode="Markdown")
        return
    
    if is_under_maintenance(uid):
        await query.message.reply_text("🚧 **SYSTEM UNDER MAINTENANCE** 🚧\n\nSorry, the bot is currently undergoing maintenance. Please try again later.", parse_mode="Markdown")
        return

    if data == "check_force_join":
        is_joined = await is_user_joined_force_channels(uid, context)
        if is_joined: 
            await query.message.delete()
            settings = load_settings()
            start_msg = settings.get("welcome_message", WELCOME_MESSAGE)
            await context.bot.send_message(chat_id=uid, text=start_msg, parse_mode="HTML")
            await context.bot.send_message(chat_id=uid, text="🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))
        else:
            await query.answer("❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)
        return

    # উইথড্র কনফার্ম এবং ক্যানসেল বাটনগুলোর জন্য চেক সবার প্রথমে করতে হবে
    if data == "withdraw_confirm":
        await process_withdraw_confirm(update, context)
        return
    
    if data == "withdraw_cancel":
        await process_withdraw_cancel(update, context)
        return

    # --- INLINE WITHDRAW METHODS CALLBACKS ---
    if data.startswith("withdraw_"):
        method_name = data.split("_")[1]
        user_data = get_user(uid)
        balance = user_data.get("balance", 0.0)
        min_w, max_w = get_withdraw_limits()
        
        if balance < min_w:
            await query.answer(f"❌ Minimum withdraw is {min_w}$!", show_alert=True)
            return
            
        context.user_data["withdraw_method"] = method_name
        context.user_data["withdraw_mode"] = "amount"
        
        await query.message.reply_text(
            f"✍️ **Withdrawal Method: {method_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 Total Balance: `{balance:.4f}$`\n"
            f"📉 Minimum Withdraw: `{min_w}$`\n\n"
            f"Please enter the amount to withdraw (in $):",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        return

    if data == "back_to_menu_inline":
        await query.message.delete()
        await context.bot.send_message(
            chat_id=uid,
            text="🏠 Returning to Main Menu.",
            reply_markup=main_keyboard(uid)
        )
        return
    
    if data.startswith("pre_approve_"):
        pid = data.replace("pre_approve_", "")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 NO, BACK", callback_data=f"back_admin_{pid}", style="primary"),
                InlineKeyboardButton("✅ YES, CONFIRM", callback_data=f"admin_approve_{pid}", style="success")
            ]
        ])
        await query.message.edit_text("❓ **Are you sure? You want to CONFIRM this payment?**", reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("pre_reject_"):
        pid = data.replace("pre_reject_", "")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 NO, BACK", callback_data=f"back_admin_{pid}", style="primary"),
                InlineKeyboardButton("❌ YES, REJECT", callback_data=f"admin_reject_{pid}", style="danger")
            ]
        ])
        await query.message.edit_text("❓ **Are you sure? You want to REJECT this payment?**", reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("back_admin_"):
        pid = data.replace("back_admin_", "")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ CANCEL", callback_data=f"pre_reject_{pid}", style="danger"),
                InlineKeyboardButton("✅ CONFIRM", callback_data=f"pre_approve_{pid}", style="success")
            ]
        ])
        await query.message.edit_text("⚠️ **Action Cancelled. Decision again:**", reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("admin_approve_"):
        payment_id = data.replace("admin_approve_", "")
        await admin_approve_withdraw(update, context, payment_id)
        return
    
    if data.startswith("admin_reject_"):
        payment_id = data.replace("admin_reject_", "")
        await admin_reject_withdraw(update, context, payment_id)
        return

    if data == "admin_back_to_config":
        context.user_data.clear()
        context.user_data["admin_mode"] = "main"
        await query.message.reply_text("🔙 Back to admin panel.", reply_markup=admin_main_keyboard())
        return

    if data == "same_range":
        settings = load_settings()
        cooldown = settings.get("cooldown_time", 4.0)
        current_time = time.time()
        time_passed = current_time - last_request_time.get(uid, 0.0)
        
        if time_passed < cooldown:
            wait_time = round(cooldown - time_passed, 1)
            await query.answer(f"⏳ Please wait {wait_time}s before changing number.", show_alert=True)
            return

        last_request_time[uid] = current_time
        r_text = last_range.get(uid)
        if r_text:
            await query.answer("🔄 Changing number...")
            await request_queue.put({
                'type': 'process_numbers', 
                'update': update, 
                'context': context, 
                'range_text': r_text, 
                'count': settings.get("numbers_per_request", 1),
                'edit_message': query.message
            })

    elif data == "back_to_apps":
        import time as _time
        cache_age = _time.monotonic() - _ranges_cache["updated_at"]
        if _ranges_cache["data"] and cache_age < 300:
            top_ranges_by_app = _ranges_cache["data"]
        else:
            top_ranges_by_app, err = await fetch_top55_ranges_by_app()
            if err or not top_ranges_by_app:
                top_ranges_by_app, err = await fetch_top55_ranges_by_app()
            if top_ranges_by_app:
                _ranges_cache["data"] = top_ranges_by_app
                _ranges_cache["updated_at"] = _time.monotonic()
            else:
                await query.edit_message_text(
                    "❌ <b>Could not load ranges.</b>\n\n"
                    "<blockquote>Please try again in a moment.</blockquote>",
                    parse_mode="HTML"
                )
                return
        context.user_data["top_ranges_by_app"] = top_ranges_by_app
        buttons = build_app_buttons_from_cache(top_ranges_by_app)
        keyboard = InlineKeyboardMarkup(buttons)
        msg = (
            f"📞 <b>SELECT APP TO GET NUMBER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)
        return

    elif data.startswith("sel_app_"):
        app_name = data[len("sel_app_"):]
        cached = context.user_data.get("top_ranges_by_app", {})
        if app_name in cached:
            info = cached[app_name]
            ranges = info["ranges"]
        else:
            try:
                fresh_data, fetch_err = await fetch_top55_ranges_by_app()
                if fresh_data and app_name in fresh_data:
                    info  = fresh_data[app_name]
                    ranges = info["ranges"]
                    context.user_data["top_ranges_by_app"] = fresh_data
                    import time as _time2
                    _ranges_cache["data"]       = fresh_data
                    _ranges_cache["updated_at"] = _time2.monotonic()
                else:
                    ranges = []
            except Exception as e:
                await query.edit_message_text(f"❌ Failed to load ranges: {e}")
                return
        if not ranges:
            await query.edit_message_text(f"📱 {app_name} — No active ranges found.")
            return

        country_buttons_map = {}
        for rng in ranges:
            flag, name = get_country_info(rng)
            country_key = f"{flag} {name}"
            if country_key not in country_buttons_map:
                country_buttons_map[country_key] = []
            country_buttons_map[country_key].append(rng)

        buttons = []
        row = []
        if "country_ranges" not in context.user_data:
            context.user_data["country_ranges"] = {}

        for country_label, rng_list in country_buttons_map.items():
            idx = len(context.user_data["country_ranges"]) + 1
            idx_str = str(idx)
            context.user_data["country_ranges"][idx_str] = {
                "app": app_name,
                "label": country_label,
                "ranges": rng_list
            }
            
            btn_label = f"{country_label}"
            row.append(InlineKeyboardButton(btn_label, callback_data=f"sel_cty_{idx_str}", style="danger"))
            
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton("« Back", callback_data="back_to_apps", style="primary")])
        keyboard = InlineKeyboardMarkup(buttons)
        context.user_data["selected_app"] = app_name
        msg = (
            f"🌎 <b>Select Country for {app_name}:</b>"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)
        return

    elif data.startswith("sel_cty_"):
        settings = load_settings()
        cooldown = settings.get("cooldown_time", 4.0)
        current_time = time.time()
        time_passed = current_time - last_request_time.get(uid, 0.0)
        
        if time_passed < cooldown:
            wait_time = round(cooldown - time_passed, 1)
            await query.answer(f"⏳ Please wait {wait_time}s before requesting a new number.", show_alert=True)
            return

        idx_str = data[len("sel_cty_"):]
        cty_info = context.user_data.get("country_ranges", {}).get(idx_str)
        if not cty_info:
            await query.edit_message_text("⚠️ Session expired. Please try getting number again.")
            return
        
        app_name = cty_info["app"]
        country_label = cty_info["label"]
        country_ranges = cty_info["ranges"]

        # দেশের রেঞ্জ লিমিট সর্বোচ্চ ৪৫ থেকে কমিয়ে ৩০-এ আনা হয়েছে
        available_ranges = country_ranges[:30]
        selected_range = random.choice(available_ranges)

        try:
            await query.edit_message_text(f"⏳ Getting {app_name} number(s) for {country_label}...")
        except Exception:
            pass

        count = settings.get("numbers_per_request", 1)
        api_key, base_url = get_api_credentials()
        tasks = []
        for _ in range(count):
            tasks.append(client_async.post(
                f"{base_url}/api/getnum",
                json={"range": selected_range, "is_national": False},
                headers={"X-API-Key": api_key}
            ))
            
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        generated_nums = []
        for r in responses:
            if isinstance(r, Exception): continue
            try:
                numdata = r.json()
                ndata = numdata.get("data", {})
                full_number = ndata.get("full_number") or ndata.get("copy") or ndata.get("number") or numdata.get("full_number")
                if full_number:
                    generated_nums.append(normalize_number(full_number))
            except:
                continue

        if not generated_nums:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"sel_app_{app_name}", style="primary")]])
            await query.edit_message_text("❌ FAILED — No valid numbers could be fetched. Try again or select another country.", reply_markup=kb)
            return

        for g_num in generated_nums:
            active_numbers[g_num] = {"uid": uid, "range": selected_range}
            save_number_range_info(uid, g_num, selected_range)
        
        last_range[uid] = selected_range
        last_request_time[uid] = current_time
        add_number_taken(uid, len(generated_nums))
        
        country_flag, country_name_local = get_country_info(generated_nums[0])
        
        assign_text = (
            f"☑️ {country_flag} {country_name_local} Number selected\n"
            f"🌀 Waiting for OTP..."
        )
        
        settings = load_settings()
        otp_group_url = settings.get("otp_group_url", "https://t.me/+31eV11IT7WQzMjI9")
        channel_url = settings.get("channel_url", "https://t.me/MinoXofficial0")
        
        keyboard = []
        for g_num in generated_nums:
            if HAS_COPY_BTN:
                btn = InlineKeyboardButton(text=f"+{g_num}", copy_text=CopyTextButton(text=f"+{g_num}"))
            else:
                btn = InlineKeyboardButton(text=f"+{g_num}", callback_data=f"copy_text_{g_num}")
            keyboard.append([btn])
            
        keyboard.extend([
            [InlineKeyboardButton("🔵🟢 Change Number", callback_data="same_range", style="danger")],
            [InlineKeyboardButton("🌐 Change Country", callback_data="back_to_apps", style="success")],
            [InlineKeyboardButton("🔒 Otp Group", url=otp_group_url, style="primary")],
            [InlineKeyboardButton("🔗 Main Channel", url=channel_url, style="primary")]
        ])
        
        await query.edit_message_text(assign_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data == "edit_txt_welcome":
        context.user_data["admin_edit_mode"] = "welcome"
        await context.bot.send_message(uid, "📝 <b>নতুন Welcome Message-টি টাইপ করে পাঠান:</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
        return
    elif data == "edit_txt_otpgroup":
        context.user_data["admin_edit_mode"] = "otpgroup"
        await context.bot.send_message(uid, "🔗 <b>নতুন OTP Group লিঙ্কটি পাঠান (অবশ্যই https:// সহ):</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
        return
    elif data == "edit_txt_channel":
        context.user_data["admin_edit_mode"] = "channel"
        await context.bot.send_message(uid, "📢 <b>নতুন Channel লিঙ্কটি পাঠান (অবশ্যই https:// সহ):</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
        return
    elif data == "edit_txt_support":
        context.user_data["admin_edit_mode"] = "support"
        await context.bot.send_message(uid, "💬 <b>নতুন Support Username-টি পাঠান (@ সহ):</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    elif data.startswith("copy_name_"):
        name_to_copy = data.replace("copy_name_", "")
        await query.answer(f"✅ Copied: {name_to_copy}", show_alert=True)
    
    elif data.startswith("copy_id_"):
        id_to_copy = data.replace("copy_id_", "")
        await query.answer(f"✅ Copied ID: {id_to_copy}", show_alert=True)
    
    elif data.startswith("copy_text_"):
        text_to_copy = data.replace("copy_text_", "")
        await query.answer(f"✅ Copied: {text_to_copy}", show_alert=True)

    elif data.startswith("full_logs_"):
        target_uid = data.replace("full_logs_", "")
        stats = get_user_stats(target_uid)
        
        all_logs = load_data(ACTIVITY_LOGS_FILE)
        user_data_db = load_data(USER_DATA_FILE)
        user_info = user_data_db.get(str(target_uid), {})
        
        user_otps = [log for log in all_logs if str(log.get('uid')) == str(target_uid) and log.get('action') == "OTP_RECEIVED"]
        
        content = f"📊 USER FULL DATA REPORT 📊\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"🆔 USER TELEGRAM ID : {target_uid}\n"
        content += f"🏷️ USER NAME : {str(user_info.get('full_name', 'N/A')).upper()}\n"
        content += f"🆔 TELEGRAM USERNAME : @{str(user_info.get('username', 'NO_USERNAME')).upper()}\n"
        content += f"💰 CURRENT BALANCE : {user_info.get('balance', 0.0)}$\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"📈 SYSTEM STATUS SUMMARY:\n"
        content += f"✨ TODAY NUMBERS TAKEN : {stats['today_numbers']}\n"
        content += f"✨ TODAY OTPS RECEIVED : {stats['today_otps']}\n"
        content += f"🔥 LAST 7 DAYS NUMBERS : {stats['last7d_numbers']}\n"
        content += f"🔥 LAST 7 DAYS OTPS : {stats['last7d_otps']}\n"
        content += f"🌐 LIFETIME NUMBERS : {stats['total_numbers']}\n"
        content += f"🌐 LIFETIME OTPS : {stats['total_otps']}\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"📜 DETAILED OTP LOGS (TIME FORMAT: 12H):\n\n"
        
        if not user_otps:
            content += "❌ NO OTP DATA FOUND FOR THIS USER.\n"
        else:
            for i, log in enumerate(user_otps, 1):
                try:
                    dt_obj = datetime.fromisoformat(log['timestamp'])
                    formatted_time = dt_obj.strftime("%I:%M:%S %p")
                    date_str = dt_obj.strftime("%d/%m/%Y")
                    details = log.get('details', {})
                    content += f"{i}. DATE: {date_str} | TIME: {formatted_time}\n"
                    content += f"   📞 NUMBER: {details.get('number', 'N/A')}\n"
                    content += f"   🔑 OTP: {details.get('otp', 'N/A')}\n"
                    content += f"   📩 SMS: {details.get('sms', 'N/A')}\n"
                    content += f"   -----------------------------------\n"
                except: continue

        content += f"\n\n🚀 GENERATED BY FAST X OTP NETWORK ⚡"
        
        file = io.BytesIO(content.encode("utf-8"))
        file.name = f"USER_{target_uid}_FULL_DATA.txt"
        
        await context.bot.send_document(
            chat_id=uid,
            document=file,
            caption=f"✅ <b>ALL DATA FOR USER:</b> <code>{target_uid}</code>",
            parse_mode="HTML"
        )

# ==================== ACTIVE DATABASE OPTIMIZER ====================

async def optimize_database_system(chat_id):
    data = load_data()
    active_numbers.clear()
    
    users = data.setdefault("users", [])
    balances = data.setdefault("balances", {})
    for uid in list(balances.keys()):
        if uid not in users:
            del balances[uid]
    
    save_data(data)

# ==================== MAIN & POST INIT SECTION ====================

async def post_init(application): 
    for _ in range(20):
        asyncio.create_task(worker())
    asyncio.create_task(monitor_loop(application))
    asyncio.create_task(_bg_refresh_ranges())

def main():
    request_config = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0)
    
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request_config)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get1number", get1number_command))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 BOT RUNNING...")  
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
