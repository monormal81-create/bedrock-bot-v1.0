# ⛏️ بوت مودات Minecraft Bedrock

بوت تيليغرام يستقبل وصف المود ويرسل ملف `.mcpack` جاهز للتثبيت.

## الملفات
```
bedrock-bot/
├── bot.py           ← البوت الرئيسي
├── pack_builder.py  ← يبني ملف .mcpack
├── requirements.txt ← المكتبات
└── README.md
```

## الإعداد

### 1. احصل على التوكنات
- **Telegram Token**: من @BotFather في تيليغرام
- **Anthropic API Key**: من console.anthropic.com

### 2. ثبّت المكتبات
```bash
pip install -r requirements.txt
```

### 3. شغّل البوت

**على Linux/Mac:**
```bash
export TELEGRAM_TOKEN="توكنك_هنا"
export ANTHROPIC_API_KEY="مفتاحك_هنا"
python bot.py
```

**على Windows:**
```cmd
set TELEGRAM_TOKEN=توكنك_هنا
set ANTHROPIC_API_KEY=مفتاحك_هنا
python bot.py
```

## النشر على Railway (مجاني)
1. ارفع المجلد على GitHub
2. اذهب لـ railway.app وأنشئ مشروع جديد
3. أضف المتغيرات في Variables:
   - `TELEGRAM_TOKEN`
   - `ANTHROPIC_API_KEY`
4. Railway يشغّله تلقائياً ✅

## الأوامر
- `/start` — ترحيب وشرح
- `/help`  — أمثلة وتعليمات
- `/reset` — مسح المحادثة
