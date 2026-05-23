"""
bot.py - بوت تيليغرام لتوليد مودات Minecraft Bedrock
يستخدم Google Gemini API (مجاني 100%)
"""

import os
import logging
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from pack_builder import process_ai_response

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["8628021629:AAElS1woQlPYq2jx981HTaNPmlKaJVR58Z0"]
GEMINI_KEY = os.environ["AIzaSyCQP2jaIHG5FnoOsTdxop3BTqR0PSk0iIE"]

client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """انت ذكاء اصطناعي متخصص حصريا في توليد Minecraft Bedrock Edition Add-ons.
عندما يصف المستخدم مود، تولد الملفات الكاملة الجاهزة للاستخدام.

قواعد صارمة:
1. قبل كل ملف اكتب مساره هكذا:
   BP/entities/my_entity.json
2. بعده ضع الكود في كتلة json
3. لا تستخدم ... ابدا - الكود كامل دائما
4. لكل manifest.json ولد UUIDs حقيقية
5. استخدم components مدعومة في Bedrock فقط
6. رتب: اولا BP ثم RP
7. في النهاية اضف طريقة التثبيت

اجب باللغة العربية دائما."""

user_histories: dict[int, list] = {}

WELCOME_TEXT = """مرحبا في مولد مودات Bedrock!

كيف يعمل؟
1 - صف المود الذي تريده
2 - انتظر 20-30 ثانية
3 - استقبل ملف mcpack جاهز!

امثلة:
- اصنع سيف نار يشعل الاعداء
- اريد تنينا يتبعني ويهاجم الاعداء
- اصنع درعا يمنح الطيران

اوامر: /help /reset"""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text(WELCOME_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "انواع المودات:\n"
        "- ايتمز: سيوف، دروع، اطعمة\n"
        "- كيانات: مخلوقات جديدة\n"
        "- وصفات Crafting Table\n\n"
        "بعد التثبيت فعل:\n"
        "- Beta APIs\n"
        "- Upcoming Creator Features"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text("تم مسح المحادثة. ابدا من جديد!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_msg = update.message.text.strip()

    if user_id not in user_histories:
        user_histories[user_id] = []

    status_msg = await update.message.reply_text("جاري توليد المود...")
    ai_text = ""

    try:
        history = user_histories[user_id].copy()
        history.append({"role": "user", "parts": [{"text": user_msg}]})

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=4000,
            )
        )

        ai_text = response.text

        user_histories[user_id].append({"role": "user", "parts": [{"text": user_msg}]})
        user_histories[user_id].append({"role": "model", "parts": [{"text": ai_text}]})

        await status_msg.edit_text("يبني ملف mcpack...")

        mcpack_path, files = process_ai_response(ai_text)

        file_list = "\n".join(f"- {p}" for p in files.keys())
        caption = (
            f"ملف المود جاهز!\n\n"
            f"الملفات ({len(files)}):\n{file_list}\n\n"
            f"افتح الملف مباشرة لتثبيته في ماين كرافت\n"
            f"فعل Beta APIs في اعدادات العالم"
        )

        with open(mcpack_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(mcpack_path),
                caption=caption,
            )

        await status_msg.delete()
        os.remove(mcpack_path)

    except ValueError as e:
        log.warning(f"No files parsed: {e}")
        await status_msg.delete()
        if ai_text:
            for i in range(0, len(ai_text), 4096):
                await update.message.reply_text(ai_text[i:i+4096])
        await update.message.reply_text("تعذر بناء الملف تلقائيا. الكود اعلاه جاهز للنسخ.")

    except Exception as e:
        log.error(f"Error: {e}", exc_info=True)
        await status_msg.edit_text(f"حدث خطا:\n{str(e)[:300]}\n\nجرب /reset")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("البوت يعمل...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
