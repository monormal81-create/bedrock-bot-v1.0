import os, logging
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pack_builder import process_ai_response

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["hidencloud"]
client = OpenAI(
    api_key=os.environ["zada"],
    base_url="https://openrouter.ai/api/v1"
)

PROMPT = "انت خبير في Minecraft Bedrock Add-ons. اكتب مسار كل ملف قبله ثم الكود في كتلة json. لا تستخدم ... الكود كامل دائما. ولد UUIDs حقيقية. استخدم Bedrock components فقط. اجب بالعربية."

histories = {}

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_user.id] = []
    await update.message.reply_text("مرحبا! صف المود وسارسل ملف mcpack جاهز!\nمثال: اصنع سيف نار يشعل الاعداء\n/reset لمسح المحادثة")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_user.id] = []
    await update.message.reply_text("تم المسح!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text.strip()
    if uid not in histories:
        histories[uid] = []
    status = await update.message.reply_text("جاري توليد المود...")
    ai_text = ""
    try:
        messages = [{"role": "system", "content": PROMPT}]
        for h in histories[uid]:
            messages.append(h)
        messages.append({"role": "user", "content": msg})

        response = client.chat.completions.create(
            model="google/gemma-3-4b-it:free",
            messages=messages,
            max_tokens=4000
        )
        ai_text = response.choices[0].message.content

        histories[uid].append({"role": "user", "content": msg})
        histories[uid].append({"role": "assistant", "content": ai_text})

        await status.edit_text("يبني ملف mcpack...")
        path, files = process_ai_response(ai_text)
        cap = (
            f"الملف جاهز!\nالملفات ({len(files)}):\n"
            + "\n".join(f"- {p}" for p in files.keys())
            + "\n\nافتحه لتثبيته في ماين كرافت\nفعل Beta APIs في اعدادات العالم"
        )
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, filename=os.path.basename(path), caption=cap)
        await status.delete()
        os.remove(path)

    except ValueError:
        await status.delete()
        if ai_text:
            for i in range(0, len(ai_text), 4096):
                await update.message.reply_text(ai_text[i:i+4096])
        await update.message.reply_text("تعذر بناء الملف تلقائيا. الكود اعلاه جاهز للنسخ.")

    except Exception as e:
        log.error(f"Error: {e}", exc_info=True)
        await status.edit_text(f"حدث خطا:\n{str(e)[:300]}\n\nجرب /reset")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("يعمل مع OpenRouter...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
