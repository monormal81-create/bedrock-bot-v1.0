"""
bot.py — بوت تيليغرام لتوليد مودات Minecraft Bedrock
يستخدم Google Gemini API (مجاني 100%)
"""

import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from pack_builder import process_ai_response

# ── إعداد اللوق ────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── مفاتيح API ────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["8729332673:AAE3My-MPVUKpqLuC_0-2iMJxyTev8JGlGU"]
GEMINI_KEY     = os.environ["AIzaSyCQP2jaIHG5FnoOsTdxop3BTqR0PSk0iIE"]

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""أنت ذكاء اصطناعي متخصص حصرياً في توليد Minecraft Bedrock Edition Add-ons.

مهمتك: عندما يصف المستخدم مود أو إضافة، تولّد الملفات الكاملة الجاهزة للاستخدام.

قواعد الإخراج الصارمة:
1. قبل كل ملف اكتب مساره بالضبط هكذا:
   📁 BP/entities/my_entity.json

2. بعد المسار مباشرةً ضع الكود في كتلة:
   ```json
   { ... }
   ```

3. لا تستخدم ... أو placeholders أبداً — الكود كامل دائماً.

4. لكل manifest.json ولّد UUIDs حقيقية بصيغة: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
   مثال: "uuid": "a3f2b1c4-d5e6-4f78-9a0b-c1d2e3f4a5b6"

5. استخدم format_version الصحيح:
   - entities BP: "1.19.0"
   - manifest: "2"
   - items: "1.20.0"
   - RP entity client: "1.10.0"

6. استخدم components مدعومة في Bedrock فقط (وليس Java).

7. رتّب الملفات: أولاً BP ثم RP.

8. في النهاية أضف قسم "📋 طريقة التثبيت:" بخطوات واضحة.

الملفات الأساسية لأي Add-on:
- BP/manifest.json (إلزامي)
- BP/entities/اسم.json (للكيانات)
- BP/items/اسم.json (للأيتمز)
- RP/manifest.json (إلزامي إذا احتاج textures)
- RP/entity/اسم.entity.json (للكيانات)

أجب باللغة العربية دائماً."""
)

# ── تخزين جلسات المستخدمين ────────────────────────────
# كل مستخدم له chat session منفصلة تحتفظ بالتاريخ
user_chats: dict[int, any] = {}

def get_chat(user_id: int):
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
    return user_chats[user_id]

# ── نصوص البوت ────────────────────────────────────────
WELCOME_TEXT = """⛏️ *مرحباً في مولّد مودات Bedrock!*

أنا ذكاء اصطناعي متخصص في صنع مودات Minecraft Bedrock Edition.

*كيف يعمل؟*
1️⃣ صف المود الذي تريده بالعربي
2️⃣ انتظر 20\-30 ثانية
3️⃣ استقبل ملف \.mcpack جاهز للتثبيت\!

*أمثلة:*
• اصنع سيف نار يشعل الأعداء
• أريد تنيناً صغيراً يتبعني ويهاجم الأعداء
• اصنع درعاً يمنح الطيران والسرعة

*أوامر:*
/start — الرسالة الترحيبية
/help — مساعدة وأمثلة
/reset — مسح المحادثة والبدء من جديد

اكتب طلبك الآن\! 👇"""

HELP_TEXT = """📖 *دليل الاستخدام*

*أنواع المودات التي أصنعها:*
🗡️ أيتمز — سيوف، أدوات، دروع، أطعمة
🐉 كيانات — مخلوقات جديدة، حيوانات، أعداء
🧪 وصفات — صنع أيتمز في Crafting Table
📦 Loot Tables — غنائم من الكيانات

*نصائح للحصول على أفضل نتيجة:*
✅ كن محدداً: سيف يجمّد الأعداء لمدة 3 ثوانٍ
✅ اذكر السلوك: يطير، يهاجم، يتبعك، يهرب
✅ اذكر المظهر: لون أحمر، بريق أخضر

*⚠️ مهم بعد التثبيت:*
فعّل في إعدادات العالم:
• Beta APIs ✓
• Upcoming Creator Features ✓"""


# ══════════════════════════════════════════════════════
#  Handlers
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_chats.pop(uid, None)  # مسح الجلسة القديمة
    await update.message.reply_text(WELCOME_TEXT, parse_mode="MarkdownV2")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chats.pop(update.effective_user.id, None)
    await update.message.reply_text("✅ تم مسح المحادثة. ابدأ من جديد!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = update.effective_user.id
    user_msg = update.message.text.strip()
    chat     = get_chat(user_id)

    # رسالة الحالة
    status_msg = await update.message.reply_text(
        "⚙️ *جارٍ توليد المود...*\n"
        "━━━━━━━━━━━━━━━\n"
        "🧠 يحلّل الطلب...",
        parse_mode="Markdown"
    )

    ai_text = ""

    try:
        # ── تحديث الحالة ──
        await status_msg.edit_text(
            "⚙️ *جارٍ توليد المود...*\n"
            "━━━━━━━━━━━━━━━\n"
            "✅ تحليل الطلب\n"
            "🔨 يولّد ملفات JSON...",
            parse_mode="Markdown"
        )

        # ── استدعاء Gemini ──
        response = chat.send_message(user_msg)
        ai_text  = response.text

        # ── تحديث الحالة ──
        await status_msg.edit_text(
            "⚙️ *جارٍ توليد المود...*\n"
            "━━━━━━━━━━━━━━━\n"
            "✅ تحليل الطلب\n"
            "✅ توليد JSON\n"
            "📦 يبني ملف .mcpack...",
            parse_mode="Markdown"
        )

        # ── بناء .mcpack ──
        mcpack_path, files = process_ai_response(ai_text)

        # ── تحديث الحالة ──
        await status_msg.edit_text(
            "⚙️ *جارٍ توليد المود...*\n"
            "━━━━━━━━━━━━━━━\n"
            "✅ تحليل الطلب\n"
            "✅ توليد JSON\n"
            "✅ بناء .mcpack\n"
            "📤 يرسل الملف...",
            parse_mode="Markdown"
        )

        # ── إرسال الملف ──
        file_list = "\n".join(f"  • `{p}`" for p in files.keys())
        caption = (
            f"📦 *ملف المود جاهز!*\n\n"
            f"*الملفات المضمّنة ({len(files)})：*\n"
            f"{file_list}\n\n"
            f"*طريقة التثبيت:*\n"
            f"1. حمّل الملف\n"
            f"2. افتحه مباشرةً من تيليغرام\n"
            f"3. سيُثبَّت تلقائياً في ماين كرافت ✅\n\n"
            f"⚠️ فعّل *Beta APIs* في إعدادات العالم"
        )

        with open(mcpack_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(mcpack_path),
                caption=caption,
                parse_mode="Markdown",
            )

        await status_msg.delete()
        os.remove(mcpack_path)

    except ValueError as e:
        # ما لقى ملفات — أرسل الرد نصاً
        log.warning(f"No files parsed: {e}")
        await status_msg.delete()

        if ai_text:
            chunks = [ai_text[i:i+4096] for i in range(0, len(ai_text), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)

        await update.message.reply_text(
            "⚠️ *تعذّر بناء الـ .mcpack تلقائياً*\n"
            "الكود أعلاه جاهز — انسخه يدوياً إلى الملفات.",
            parse_mode="Markdown"
        )

    except Exception as e:
        log.error(f"Error for user {user_id}: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ حدث خطأ:\n`{str(e)[:300]}`\n\nجرّب /reset وأعد الطلب.",
            parse_mode="Markdown"
        )


# ══════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("✅ البوت يعمل مع Gemini — في انتظار الرسائل...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
