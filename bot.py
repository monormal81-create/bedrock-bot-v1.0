import os
import json
import logging
import zipfile
import tempfile
import sys

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from builder.engine import build_item, build_armor, build_entity, build_recipe
from validator.validator import validate_pack

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["hidencloud"]

(
    S_MOD_TYPE,
    S_ITEM_TYPE, S_ITEM_NAME, S_ITEM_DAMAGE, S_ITEM_DURABILITY,
    S_ITEM_EFFECTS, S_ITEM_RECIPE_Q, S_ITEM_RECIPE_TYPE,
    S_ITEM_INGREDIENTS, S_ITEM_NAMESPACE,
    S_FOOD_NUTRITION, S_FOOD_EFFECTS,
    S_ARMOR_NAME, S_ARMOR_PROTECTION,
    S_ENTITY_TYPE, S_ENTITY_NAME, S_ENTITY_HEALTH, S_ENTITY_DAMAGE,
    S_ENTITY_SPEED, S_ENTITY_COLOR,
    S_CONFIRM
) = range(21)

user_data_store = {}

def kb_mod_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ آيتم (سيف/فأس/قوس)", callback_data="type_item")],
        [InlineKeyboardButton("🍖 طعام / جرعة", callback_data="type_food")],
        [InlineKeyboardButton("🛡️ درع كامل", callback_data="type_armor")],
        [InlineKeyboardButton("🐉 كيان (مخلوق)", callback_data="type_entity")],
    ])

def kb_item_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡️ سيف", callback_data="item_sword"),
         InlineKeyboardButton("🪓 فأس", callback_data="item_axe")],
        [InlineKeyboardButton("🏹 قوس", callback_data="item_bow"),
         InlineKeyboardButton("💎 آيتم عادي", callback_data="item_generic")],
    ])

def kb_damage():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("5 ضعيف", callback_data="dmg_5"),
         InlineKeyboardButton("10 متوسط", callback_data="dmg_10")],
        [InlineKeyboardButton("15 قوي", callback_data="dmg_15"),
         InlineKeyboardButton("20 أسطوري", callback_data="dmg_20")],
        [InlineKeyboardButton("30 خارق", callback_data="dmg_30")],
    ])

def kb_durability():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("250 هش", callback_data="dur_250"),
         InlineKeyboardButton("500 عادي", callback_data="dur_500")],
        [InlineKeyboardButton("1000 متين", callback_data="dur_1000"),
         InlineKeyboardButton("2000 أسطوري", callback_data="dur_2000")],
        [InlineKeyboardButton("9999 لا يكسر", callback_data="dur_9999")],
    ])

def kb_effects():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 نار", callback_data="eff_fire"),
         InlineKeyboardButton("☠️ سم", callback_data="eff_poison")],
        [InlineKeyboardButton("❄️ تجميد", callback_data="eff_freeze"),
         InlineKeyboardButton("⚡ ذبول", callback_data="eff_wither")],
        [InlineKeyboardButton("💚 شفاء", callback_data="eff_heal"),
         InlineKeyboardButton("🚫 بدون تأثير", callback_data="eff_none")],
        [InlineKeyboardButton("✅ انتهيت", callback_data="eff_done")],
    ])

def kb_recipe():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("نعم ✅", callback_data="recipe_yes"),
         InlineKeyboardButton("لا ❌", callback_data="recipe_no")],
    ])

def kb_recipe_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 Crafting Table", callback_data="recipe_shaped")],
        [InlineKeyboardButton("🔥 فرن Furnace", callback_data="recipe_furnace")],
        [InlineKeyboardButton("🎲 بدون ترتيب", callback_data="recipe_shapeless")],
    ])

def kb_entity_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👹 عدو يهاجم", callback_data="ent_hostile")],
        [InlineKeyboardButton("🐄 سلبي لا يهاجم", callback_data="ent_passive")],
        [InlineKeyboardButton("🐺 مرافق يتبعك", callback_data="ent_companion")],
    ])

def kb_health():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 ضعيف", callback_data="hp_10"),
         InlineKeyboardButton("20 عادي", callback_data="hp_20")],
        [InlineKeyboardButton("50 قوي", callback_data="hp_50"),
         InlineKeyboardButton("100 بوس", callback_data="hp_100")],
        [InlineKeyboardButton("200 أسطوري", callback_data="hp_200")],
    ])

def kb_speed():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐢 بطيء", callback_data="spd_0.2"),
         InlineKeyboardButton("🚶 عادي", callback_data="spd_0.3")],
        [InlineKeyboardButton("🏃 سريع", callback_data="spd_0.5"),
         InlineKeyboardButton("⚡ خارق", callback_data="spd_0.8")],
    ])

def kb_color():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 أحمر", callback_data="col_red"),
         InlineKeyboardButton("🔵 أزرق", callback_data="col_blue")],
        [InlineKeyboardButton("🟢 أخضر", callback_data="col_green"),
         InlineKeyboardButton("⚫ أسود", callback_data="col_black")],
        [InlineKeyboardButton("🟣 بنفسجي", callback_data="col_purple"),
         InlineKeyboardButton("🟠 برتقالي", callback_data="col_orange")],
    ])

def kb_armor_protection():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵 خفيف", callback_data="prot_low"),
         InlineKeyboardButton("🟡 متوسط", callback_data="prot_medium")],
        [InlineKeyboardButton("🔴 ثقيل", callback_data="prot_high")],
    ])

def kb_food_effects():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ سرعة", callback_data="food_speed"),
         InlineKeyboardButton("💪 قوة", callback_data="food_strength")],
        [InlineKeyboardButton("💚 تجدد", callback_data="food_regeneration"),
         InlineKeyboardButton("🔥 مقاومة نار", callback_data="food_fire_resistance")],
        [InlineKeyboardButton("👁️ رؤية ليلية", callback_data="food_night_vision"),
         InlineKeyboardButton("👻 اختفاء", callback_data="food_invisibility")],
        [InlineKeyboardButton("🚫 بدون تأثير", callback_data="food_none")],
        [InlineKeyboardButton("✅ انتهيت", callback_data="food_done")],
    ])

def kb_confirm():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ أنشئ المود!", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ ألغِ", callback_data="confirm_no")],
    ])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data_store[uid] = {"effects": [], "drops": []}
    await update.message.reply_text(
        "⛏️ مرحباً في مصنع مودات Bedrock!\n\n"
        "سأسألك خطوة بخطوة وأصنع لك ملف mcpack جاهز!\n\n"
        "اختر نوع المود:",
        reply_markup=kb_mod_type()
    )
    return S_MOD_TYPE

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data_store[uid] = {"effects": [], "drops": []}
    await update.message.reply_text("تم الإلغاء. أرسل /start للبدء من جديد.")
    return ConversationHandler.END

async def cb_mod_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    if data == "type_item":
        user_data_store[uid]["mod_type"] = "item"
        await query.edit_message_text("اختر نوع الآيتم:", reply_markup=kb_item_type())
        return S_ITEM_TYPE
    elif data == "type_food":
        user_data_store[uid]["mod_type"] = "food"
        user_data_store[uid]["item_type"] = "food"
        await query.edit_message_text("اكتب اسم الطعام أو الجرعة:")
        return S_ITEM_NAME
    elif data == "type_armor":
        user_data_store[uid]["mod_type"] = "armor"
        await query.edit_message_text("اكتب اسم مجموعة الدرع (مثال: درع التنين):")
        return S_ARMOR_NAME
    elif data == "type_entity":
        user_data_store[uid]["mod_type"] = "entity"
        await query.edit_message_text("اختر نوع الكيان:", reply_markup=kb_entity_type())
        return S_ENTITY_TYPE

async def cb_item_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["item_type"] = query.data.replace("item_", "")
    await query.edit_message_text("اكتب اسم الآيتم (مثال: سيف الجحيم):")
    return S_ITEM_NAME

async def msg_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()
    user_data_store[uid]["display_name"] = name
    item_id = ''.join(c if c.isalnum() or c=='_' else '_' for c in name.lower().replace(" ","_")) or "custom_item"
    user_data_store[uid]["item_id"] = item_id
    mod_type = user_data_store[uid].get("mod_type","item")
    item_type = user_data_store[uid].get("item_type","sword")
    if mod_type == "food" or item_type == "food":
        await update.message.reply_text(
            "اختر مستوى الشبع:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("2 قليل", callback_data="nut_2"),
                 InlineKeyboardButton("4 عادي", callback_data="nut_4")],
                [InlineKeyboardButton("8 جيد", callback_data="nut_8"),
                 InlineKeyboardButton("12 ممتاز", callback_data="nut_12")],
            ])
        )
        return S_FOOD_NUTRITION
    await update.message.reply_text("اختر قوة الضرر:", reply_markup=kb_damage())
    return S_ITEM_DAMAGE

async def cb_damage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["damage"] = int(query.data.replace("dmg_",""))
    await query.edit_message_text(f"✅ الضرر: {user_data_store[uid]['damage']}\n\nاختر المتانة:", reply_markup=kb_durability())
    return S_ITEM_DURABILITY

async def cb_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["durability"] = int(query.data.replace("dur_",""))
    await query.edit_message_text(f"✅ المتانة: {user_data_store[uid]['durability']}\n\nاختر تأثيراً عند الضرب:", reply_markup=kb_effects())
    return S_ITEM_EFFECTS

async def cb_effects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    if data in ("eff_done","eff_none"):
        await query.edit_message_text(
            f"✅ التأثيرات: {user_data_store[uid].get('effects',[]) or 'لا يوجد'}\n\nهل تريد إضافة وصفة للصنع؟",
            reply_markup=kb_recipe()
        )
        return S_ITEM_RECIPE_Q
    eff = data.replace("eff_","")
    effects = user_data_store[uid].get("effects",[])
    if eff not in effects:
        effects.append(eff)
    user_data_store[uid]["effects"] = effects
    await query.edit_message_text(
        f"✅ تمت إضافة: {eff}\nالتأثيرات: {effects}\n\nاختر تأثيراً آخر أو اضغط انتهيت:",
        reply_markup=kb_effects()
    )
    return S_ITEM_EFFECTS

async def cb_recipe_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if query.data == "recipe_no":
        user_data_store[uid]["has_recipe"] = False
        user_data_store[uid]["namespace"] = "mymod"
        return await _show_item_summary(query, uid)
    user_data_store[uid]["has_recipe"] = True
    await query.edit_message_text("اختر نوع الوصفة:", reply_markup=kb_recipe_type())
    return S_ITEM_RECIPE_TYPE

async def cb_recipe_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    recipe_type = query.data.replace("recipe_","")
    user_data_store[uid]["recipe_type"] = recipe_type
    if recipe_type == "furnace":
        await query.edit_message_text("اكتب اسم الخام (مثال: minecraft:iron_ore):")
    else:
        await query.edit_message_text(
            "اكتب المكونات مفصولة بفاصلة\n"
            "مثال: minecraft:diamond,minecraft:stick,minecraft:stick"
        )
    return S_ITEM_INGREDIENTS

async def msg_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    recipe_type = user_data_store[uid].get("recipe_type","shaped")
    if recipe_type == "furnace":
        user_data_store[uid]["input_item"] = text
    else:
        user_data_store[uid]["ingredients"] = [i.strip() for i in text.split(",")]
    user_data_store[uid]["namespace"] = "mymod"
    await update.message.reply_text(
        _item_summary_text(user_data_store[uid]),
        reply_markup=kb_confirm()
    )
    return S_CONFIRM

async def _show_item_summary(query, uid):
    await query.edit_message_text(_item_summary_text(user_data_store[uid]), reply_markup=kb_confirm())
    return S_CONFIRM

def _item_summary_text(d):
    return (
        f"📋 ملخص المود:\n━━━━━━━━━━━━━━━\n"
        f"النوع: {d.get('item_type','؟')}\n"
        f"الاسم: {d.get('display_name','؟')}\n"
        f"الضرر: {d.get('damage','-')}\n"
        f"المتانة: {d.get('durability','-')}\n"
        f"التأثيرات: {d.get('effects',[]) or 'لا يوجد'}\n"
        f"الوصفة: {'نعم' if d.get('has_recipe') else 'لا'}\n"
        f"━━━━━━━━━━━━━━━\nهل تريد إنشاء المود؟"
    )

async def cb_food_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["nutrition"] = int(query.data.replace("nut_",""))
    await query.edit_message_text(
        f"✅ الشبع: {user_data_store[uid]['nutrition']}\n\nاختر تأثيرات الطعام:",
        reply_markup=kb_food_effects()
    )
    return S_FOOD_EFFECTS

async def cb_food_effects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data.replace("food_","")
    if data in ("done","none"):
        user_data_store[uid]["namespace"] = "mymod"
        d = user_data_store[uid]
        await query.edit_message_text(
            f"📋 ملخص الطعام:\n━━━━━━━━━━━━━━━\n"
            f"الاسم: {d.get('display_name')}\n"
            f"الشبع: {d.get('nutrition',4)}\n"
            f"التأثيرات: {d.get('effects',[]) or 'لا يوجد'}\n"
            f"━━━━━━━━━━━━━━━\nهل تريد إنشاء المود؟",
            reply_markup=kb_confirm()
        )
        return S_CONFIRM
    effects = user_data_store[uid].get("effects",[])
    if data not in effects:
        effects.append(data)
    user_data_store[uid]["effects"] = effects
    await query.edit_message_text(
        f"✅ تأثير مضاف: {data}\nالتأثيرات: {effects}\n\nاختر المزيد أو اضغط انتهيت:",
        reply_markup=kb_food_effects()
    )
    return S_FOOD_EFFECTS

async def msg_armor_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()
    armor_id = ''.join(c if c.isalnum() or c=='_' else '_' for c in name.lower().replace(" ","_")) or "custom_armor"
    user_data_store[uid]["armor_name"] = armor_id
    user_data_store[uid]["display_prefix"] = name
    await update.message.reply_text("اختر مستوى الحماية:", reply_markup=kb_armor_protection())
    return S_ARMOR_PROTECTION

async def cb_armor_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["protection"] = query.data.replace("prot_","")
    user_data_store[uid]["namespace"] = "mymod"
    user_data_store[uid]["pieces"] = ["helmet","chestplate","leggings","boots"]
    d = user_data_store[uid]
    await query.edit_message_text(
        f"📋 ملخص الدرع:\n━━━━━━━━━━━━━━━\n"
        f"الاسم: {d.get('display_prefix')}\n"
        f"الحماية: {d.get('protection')}\n"
        f"القطع: خوذة + صدرية + ساقية + حذاء\n"
        f"━━━━━━━━━━━━━━━\nهل تريد إنشاء المود؟",
        reply_markup=kb_confirm()
    )
    return S_CONFIRM

async def cb_entity_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["entity_type"] = query.data.replace("ent_","")
    await query.edit_message_text("اكتب اسم الكيان (مثال: تنين الجحيم):")
    return S_ENTITY_NAME

async def msg_entity_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()
    entity_id = ''.join(c if c.isalnum() or c=='_' else '_' for c in name.lower().replace(" ","_")) or "custom_entity"
    user_data_store[uid]["display_name"] = name
    user_data_store[uid]["entity_id"] = entity_id
    await update.message.reply_text("اختر كمية الحياة:", reply_markup=kb_health())
    return S_ENTITY_HEALTH

async def cb_entity_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["health"] = int(query.data.replace("hp_",""))
    await query.edit_message_text(
        f"✅ الحياة: {user_data_store[uid]['health']}\n\nاختر قوة الضرر:",
        reply_markup=kb_damage()
    )
    return S_ENTITY_DAMAGE

async def cb_entity_damage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["damage"] = int(query.data.replace("dmg_",""))
    await query.edit_message_text(
        f"✅ الضرر: {user_data_store[uid]['damage']}\n\nاختر السرعة:",
        reply_markup=kb_speed()
    )
    return S_ENTITY_SPEED

async def cb_entity_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data_store[uid]["speed"] = float(query.data.replace("spd_",""))
    await query.edit_message_text(
        f"✅ السرعة: {user_data_store[uid]['speed']}\n\nاختر لون بيضة الإنشاء:",
        reply_markup=kb_color()
    )
    return S_ENTITY_COLOR

async def cb_entity_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    color = query.data.replace("col_","")
    user_data_store[uid]["color1"] = color
    user_data_store[uid]["color2"] = "black"
    user_data_store[uid]["namespace"] = "mymod"
    user_data_store[uid]["drops"] = [{"item":"minecraft:bone","weight":1,"min":0,"max":2}]
    d = user_data_store[uid]
    await query.edit_message_text(
        f"📋 ملخص الكيان:\n━━━━━━━━━━━━━━━\n"
        f"الاسم: {d.get('display_name')}\n"
        f"النوع: {d.get('entity_type')}\n"
        f"الحياة: {d.get('health')} ❤️\n"
        f"الضرر: {d.get('damage')}\n"
        f"السرعة: {d.get('speed')}\n"
        f"اللون: {color}\n"
        f"━━━━━━━━━━━━━━━\nهل تريد إنشاء المود؟",
        reply_markup=kb_confirm()
    )
    return S_CONFIRM

async def cb_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if query.data == "confirm_no":
        await query.edit_message_text("تم الإلغاء. أرسل /start للبدء من جديد.")
        return ConversationHandler.END
    await query.edit_message_text("⚙️ جارٍ بناء المود...")
    d = user_data_store[uid]
    mod_type = d.get("mod_type","item")
    try:
        files = {}
        if mod_type == "item":
            files = build_item(d)
            if d.get("has_recipe"):
                files.update(build_recipe(d))
        elif mod_type == "food":
            files = build_item(d)
        elif mod_type == "armor":
            files = build_armor(d)
        elif mod_type == "entity":
            files = build_entity(d)

        try:
            textures = generate_all_textures(d)
            files.update(textures)
        except Exception as tex_err:
            log.warning(f"Texture: {tex_err}")

        validation = validate_pack(files)
        if not validation.is_valid:
            await query.edit_message_text(
                f"❌ فشل الفحص النهائي!\n\n{validation.summary()}\n\nأرسل /start وحاول مجدداً."
            )
            return ConversationHandler.END

        mcpack_path = _build_mcpack(files, d.get("display_name","addon"))
        await query.message.reply_text(validation.summary())
        file_list = "\n".join(f"• {p}" for p in files if files[p] is not None)
        caption = (
            f"📦 المود جاهز!\n\nالملفات:\n{file_list}\n\n"
            f"افتح الملف لتثبيته في ماين كرافت ✅\n"
            f"فعّل Beta APIs في إعدادات العالم"
        )
        with open(mcpack_path,"rb") as f:
            await query.message.reply_document(
                document=f,
                filename=os.path.basename(mcpack_path),
                caption=caption
            )
        os.remove(mcpack_path)
        await query.edit_message_text("✅ تم إنشاء المود بنجاح!")
    except Exception as e:
        log.error(f"Build error: {e}", exc_info=True)
        await query.edit_message_text(f"❌ خطأ:\n{str(e)[:300]}\n\nأرسل /start وحاول مجدداً.")
    return ConversationHandler.END

def _build_mcpack(files, name):
    safe_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in name)[:30] or "addon"
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, f"{safe_name}.mcpack")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            if content is None:
                zf.writestr(path, b'')
                continue
            zf.writestr(path, json.dumps(content,indent=2,ensure_ascii=False).encode("utf-8"))
    return out

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            S_MOD_TYPE: [CallbackQueryHandler(cb_mod_type)],
            S_ITEM_TYPE: [CallbackQueryHandler(cb_item_type)],
            S_ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_item_name)],
            S_ITEM_DAMAGE: [CallbackQueryHandler(cb_damage, pattern="^dmg_")],
            S_ITEM_DURABILITY: [CallbackQueryHandler(cb_durability, pattern="^dur_")],
            S_ITEM_EFFECTS: [CallbackQueryHandler(cb_effects, pattern="^eff_")],
            S_ITEM_RECIPE_Q: [CallbackQueryHandler(cb_recipe_q, pattern="^recipe_")],
            S_ITEM_RECIPE_TYPE: [CallbackQueryHandler(cb_recipe_type, pattern="^recipe_")],
            S_ITEM_INGREDIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_ingredients)],
            S_FOOD_NUTRITION: [CallbackQueryHandler(cb_food_nutrition, pattern="^nut_")],
            S_FOOD_EFFECTS: [CallbackQueryHandler(cb_food_effects, pattern="^food_")],
            S_ARMOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_armor_name)],
            S_ARMOR_PROTECTION: [CallbackQueryHandler(cb_armor_protection, pattern="^prot_")],
            S_ENTITY_TYPE: [CallbackQueryHandler(cb_entity_type, pattern="^ent_")],
            S_ENTITY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_entity_name)],
            S_ENTITY_HEALTH: [CallbackQueryHandler(cb_entity_health, pattern="^hp_")],
            S_ENTITY_DAMAGE: [CallbackQueryHandler(cb_entity_damage, pattern="^dmg_")],
            S_ENTITY_SPEED: [CallbackQueryHandler(cb_entity_speed, pattern="^spd_")],
            S_ENTITY_COLOR: [CallbackQueryHandler(cb_entity_color, pattern="^col_")],
            S_CONFIRM: [CallbackQueryHandler(cb_confirm, pattern="^confirm_")],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True
    )
    app.add_handler(conv)
    log.info("✅ البوت يعمل بدون AI!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
