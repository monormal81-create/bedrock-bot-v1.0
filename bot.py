"""
bot.py — بوت تيليغرام لصنع مودات Minecraft Bedrock
بدون أي AI — نظام قوالب + أسئلة تفاعلية
"""

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
from pixel_art.generator import generate_all_textures
from bundle_manager import merge_packs, get_bundle_summary
from db_manager import save_mod, get_user_mods, get_mod_by_id, delete_mod, get_mods_count

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["hidencloud"]

# ── حالات المحادثة ─────────────────────────────────────
(
    S_MOD_TYPE,
    S_ITEM_TYPE, S_ITEM_NAME, S_ITEM_DAMAGE, S_ITEM_DURABILITY,
    S_ITEM_EFFECTS, S_ITEM_RECIPE_Q, S_ITEM_RECIPE_TYPE,
    S_ITEM_INGREDIENTS, S_ITEM_NAMESPACE,
    S_FOOD_NUTRITION, S_FOOD_SATURATION, S_FOOD_EFFECTS,
    S_ARMOR_NAME, S_ARMOR_PIECES, S_ARMOR_PROTECTION, S_ARMOR_NAMESPACE,
    S_ENTITY_TYPE, S_ENTITY_NAME, S_ENTITY_HEALTH, S_ENTITY_DAMAGE,
    S_ENTITY_SPEED, S_ENTITY_COLOR, S_ENTITY_DROPS, S_ENTITY_NAMESPACE,
    S_CONFIRM
) = range(26)

# تخزين بيانات المستخدم
user_data_store: dict[int, dict] = {}
bundle_store: dict = {}


# ════════════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════════════

def kb_mod_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ آيتم (سيف/فأس/قوس...)", callback_data="type_item")],
        [InlineKeyboardButton("🍖 طعام / جرعة", callback_data="type_food")],
        [InlineKeyboardButton("🛡️ درع كامل", callback_data="type_armor")],
        [InlineKeyboardButton("🐉 كيان (مخلوق)", callback_data="type_entity")],
    ])

def kb_item_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡️ سيف", callback_data="item_sword"),
         InlineKeyboardButton("🪓 فأس", callback_data="item_axe")],
        [InlineKeyboardButton("🏹 قوس", callback_data="item_bow"),
         InlineKeyboardButton("🛡️ ترس", callback_data="item_shield")],
        [InlineKeyboardButton("💎 آيتم عادي", callback_data="item_generic")],
    ])

def kb_damage():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("5 (ضعيف)", callback_data="dmg_5"),
         InlineKeyboardButton("10 (متوسط)", callback_data="dmg_10")],
        [InlineKeyboardButton("15 (قوي)", callback_data="dmg_15"),
         InlineKeyboardButton("20 (أسطوري)", callback_data="dmg_20")],
        [InlineKeyboardButton("30 (خارق)", callback_data="dmg_30")],
    ])

def kb_durability():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("250 (هش)", callback_data="dur_250"),
         InlineKeyboardButton("500 (عادي)", callback_data="dur_500")],
        [InlineKeyboardButton("1000 (متين)", callback_data="dur_1000"),
         InlineKeyboardButton("2000 (أسطوري)", callback_data="dur_2000")],
        [InlineKeyboardButton("غير قابل للكسر ♾️", callback_data="dur_9999")],
    ])

def kb_effects():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 نار", callback_data="eff_fire"),
         InlineKeyboardButton("☠️ سم", callback_data="eff_poison")],
        [InlineKeyboardButton("❄️ تجميد", callback_data="eff_freeze"),
         InlineKeyboardButton("⚡ ذبول", callback_data="eff_wither")],
        [InlineKeyboardButton("💚 شفاء", callback_data="eff_heal"),
         InlineKeyboardButton("🚫 بدون تأثير", callback_data="eff_none")],
        [InlineKeyboardButton("✅ انتهيت من التأثيرات", callback_data="eff_done")],
    ])

def kb_recipe():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("نعم ✅", callback_data="recipe_yes"),
         InlineKeyboardButton("لا ❌", callback_data="recipe_no")],
    ])

def kb_recipe_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 Crafting Table", callback_data="recipe_shaped")],
        [InlineKeyboardButton("🔥 فرن (Furnace)", callback_data="recipe_furnace")],
        [InlineKeyboardButton("🎲 بدون ترتيب", callback_data="recipe_shapeless")],
    ])

def kb_entity_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👹 عدو (يهاجم)", callback_data="ent_hostile")],
        [InlineKeyboardButton("🐄 سلبي (لا يهاجم)", callback_data="ent_passive")],
        [InlineKeyboardButton("🐺 مرافق (يتبعك)", callback_data="ent_companion")],
    ])

def kb_health():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 ❤️ (ضعيف)", callback_data="hp_10"),
         InlineKeyboardButton("20 ❤️ (عادي)", callback_data="hp_20")],
        [InlineKeyboardButton("50 ❤️ (قوي)", callback_data="hp_50"),
         InlineKeyboardButton("100 ❤️ (بوس)", callback_data="hp_100")],
        [InlineKeyboardButton("200 ❤️ (أسطوري)", callback_data="hp_200")],
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

def kb_confirm():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ أنشئ المود!", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ ألغِ", callback_data="confirm_no")],
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


# ════════════════════════════════════════════════════════
#  START
# ════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data_store[uid] = {"effects": [], "drops": []}
    bundle_store[uid] = []
    await update.message.reply_text(
        "⛏️ مرحباً في مصنع مودات Bedrock!\n\n"
        "اختر وضع الإنشاء:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 مود واحد", callback_data="mode_single")],
            [InlineKeyboardButton("🎁 حزمة مودات متعددة", callback_data="mode_bundle")],
        ])
    )
    return S_BUNDLE_MODE

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data_store[uid] = {"effects": [], "drops": []}
    await update.message.reply_text("تم الإلغاء. أرسل /start للبدء من جديد.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  MOD TYPE SELECTION
# ════════════════════════════════════════════════════════



# ════════════════════════════════════════════════════════
#  BUNDLE MODE HANDLERS
# ════════════════════════════════════════════════════════

async def cb_bundle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "mode_single":
        # وضع مود واحد عادي
        user_data_store[uid] = {"effects": [], "drops": []}
        await query.edit_message_text("اختر نوع المود:", reply_markup=kb_mod_type())
        return S_MOD_TYPE

    elif query.data == "mode_bundle":
        # وضع الحزمة
        bundle_store[uid] = []
        await query.edit_message_text(
            "🎁 *وضع الحزمة*\n\n"
            "أضف المودات التي تريدها في الحزمة واحداً تلو الآخر.\n"
            "عندما تنتهي اضغط *إنشاء الحزمة*\n\n"
            "ابدأ بإضافة أول مود:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ آيتم", callback_data="badd_item"),
                 InlineKeyboardButton("🍖 طعام", callback_data="badd_food")],
                [InlineKeyboardButton("🛡️ درع", callback_data="badd_armor"),
                 InlineKeyboardButton("🐉 كيان", callback_data="badd_entity")],
            ])
        )
        return S_BUNDLE_ADD


async def cb_bundle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل نوع المود المراد إضافته للحزمة"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "bundle_build":
        # بناء الحزمة
        if not bundle_store.get(uid):
            await query.edit_message_text("⚠️ لم تضف أي مود بعد! أضف مود أولاً.")
            return S_BUNDLE_ADD

        summary = get_bundle_summary(bundle_store[uid])
        await query.edit_message_text(
            f"{summary}\n\nهل تريد إنشاء الحزمة؟",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ إنشاء الحزمة!", callback_data="bundle_confirm")],
                [InlineKeyboardButton("➕ أضف مود آخر", callback_data="bundle_more")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="bundle_cancel")],
            ])
        )
        return S_BUNDLE_CONFIRM

    # حدد نوع المود وابدأ flow العادي
    type_map = {
        "badd_item": "item", "badd_food": "food",
        "badd_armor": "armor", "badd_entity": "entity"
    }
    mod_type = type_map.get(query.data, "item")
    user_data_store[uid] = {"effects": [], "drops": [], "mod_type": mod_type, "in_bundle": True}

    if mod_type == "item":
        await query.edit_message_text("اختر نوع الآيتم:", reply_markup=kb_item_type())
        return S_ITEM_TYPE
    elif mod_type == "food":
        user_data_store[uid]["item_type"] = "food"
        await query.edit_message_text("اكتب اسم الطعام أو الجرعة:")
        return S_ITEM_NAME
    elif mod_type == "armor":
        await query.edit_message_text("اكتب اسم مجموعة الدرع (مثال: درع التنين):")
        return S_ARMOR_NAME
    elif mod_type == "entity":
        await query.edit_message_text("اختر نوع الكيان:", reply_markup=kb_entity_type())
        return S_ENTITY_TYPE


async def cb_bundle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يبني الحزمة الكاملة"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "bundle_cancel":
        await query.edit_message_text("تم الإلغاء. أرسل /start للبدء من جديد.")
        return ConversationHandler.END

    if query.data == "bundle_more":
        await query.edit_message_text(
            f"أضف مود آخر للحزمة ({len(bundle_store.get(uid,[]))} مود حتى الآن):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ آيتم", callback_data="badd_item"),
                 InlineKeyboardButton("🍖 طعام", callback_data="badd_food")],
                [InlineKeyboardButton("🛡️ درع", callback_data="badd_armor"),
                 InlineKeyboardButton("🐉 كيان", callback_data="badd_entity")],
                [InlineKeyboardButton("🏗️ إنشاء الحزمة الآن", callback_data="bundle_build")],
            ])
        )
        return S_BUNDLE_ADD

    # bundle_confirm — ابنِ الحزمة
    mods = bundle_store.get(uid, [])
    if not mods:
        await query.edit_message_text("❌ لا يوجد مودات في الحزمة!")
        return ConversationHandler.END

    await query.edit_message_text(f"⚙️ جارٍ بناء الحزمة ({len(mods)} مودات)...")

    try:
        # ابنِ كل مود وجمّع ملفاته
        all_mod_files = []
        for mod_data in mods:
            mod_type = mod_data.get("mod_type", "item")
            if mod_type in ("item", "food"):
                files = build_item(mod_data)
                if mod_data.get("has_recipe"):
                    files.update(build_recipe(mod_data))
            elif mod_type == "armor":
                files = build_armor(mod_data)
            elif mod_type == "entity":
                files = build_entity(mod_data)
            else:
                files = build_item(mod_data)

            # أضف الصور
            try:
                textures = generate_all_textures(mod_data)
                files.update(textures)
            except Exception as tex_err:
                log.warning(f"Texture warning: {tex_err}")

            all_mod_files.append(files)

        # ادمج كل الملفات
        merged_files = merge_packs(all_mod_files)

        # فحص نهائي
        validation = validate_pack(merged_files)
        await query.message.reply_text(validation.summary())

        # بناء الـ mcpack
        pack_name = f"bundle_{len(mods)}_mods"
        mcpack_path = _build_mcpack(merged_files, pack_name)

        # إرسال الملف
        mod_names = ", ".join(m.get("display_name", "مود") for m in mods)
        mod_list = "\n".join(f"• {m.get('display_name', 'مود')}" for m in mods)
        caption = (
            f"🎁 الحزمة جاهزة!\n\n"
            f"تحتوي على {len(mods)} مودات:\n"
            f"{mod_list}\n\n"
            f"افتح الملف لتثبيته في ماين كرافت\n"
            f"فعل Beta APIs في اعدادات العالم"
        )

        with open(mcpack_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=os.path.basename(mcpack_path),
                caption=f"🎁 الحزمة جاهزة! {len(mods)} مودات: {mod_names}"
            )

        os.remove(mcpack_path)
        bundle_store[uid] = []
        await query.edit_message_text(f"✅ تم إنشاء الحزمة بنجاح! ({len(mods)} مودات)")

    except Exception as e:
        log.error(f"Bundle error: {e}", exc_info=True)
        await query.edit_message_text(f"❌ خطأ في بناء الحزمة:\n{str(e)[:300]}")

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
        await query.edit_message_text("اكتب اسم الطعام أو الجرعة (مثال: تفاحة السحر):")
        return S_ITEM_NAME

    elif data == "type_armor":
        user_data_store[uid]["mod_type"] = "armor"
        await query.edit_message_text("اكتب اسم مجموعة الدرع (مثال: درع التنين):")
        return S_ARMOR_NAME

    elif data == "type_entity":
        user_data_store[uid]["mod_type"] = "entity"
        await query.edit_message_text("اختر نوع الكيان:", reply_markup=kb_entity_type())
        return S_ENTITY_TYPE


# ════════════════════════════════════════════════════════
#  ITEM FLOW
# ════════════════════════════════════════════════════════

async def cb_item_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    item_type = query.data.replace("item_", "")
    user_data_store[uid]["item_type"] = item_type
    await query.edit_message_text("اكتب اسم الآيتم (مثال: سيف الجحيم):")
    return S_ITEM_NAME

async def msg_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()
    user_data_store[uid]["display_name"] = name
    # توليد ID من الاسم
    item_id = name.lower().replace(" ", "_").replace("ا","a").replace("ل","l")
    item_id = ''.join(c if c.isalnum() or c=='_' else '' for c in item_id) or "custom_item"
    user_data_store[uid]["item_id"] = item_id

    mod_type = user_data_store[uid].get("mod_type", "item")
    item_type = user_data_store[uid].get("item_type", "sword")

    if mod_type == "food" or item_type == "food":
        await update.message.reply_text("كم قيمة الشبع؟ (1-20)\nاكتب رقماً أو اضغط:")
        await update.message.reply_text(
            "اختر مستوى الشبع:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("2 (قليل)", callback_data="nut_2"),
                 InlineKeyboardButton("4 (عادي)", callback_data="nut_4")],
                [InlineKeyboardButton("8 (جيد)", callback_data="nut_8"),
                 InlineKeyboardButton("12 (ممتاز)", callback_data="nut_12")],
            ])
        )
        return S_FOOD_NUTRITION

    await update.message.reply_text("اختر قوة الضرر:", reply_markup=kb_damage())
    return S_ITEM_DAMAGE

async def cb_damage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    damage = int(query.data.replace("dmg_", ""))
    user_data_store[uid]["damage"] = damage
    await query.edit_message_text(f"✅ الضرر: {damage}\n\nاختر المتانة:", reply_markup=kb_durability())
    return S_ITEM_DURABILITY

async def cb_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    dur = int(query.data.replace("dur_", ""))
    user_data_store[uid]["durability"] = dur
    await query.edit_message_text(f"✅ المتانة: {dur}\n\nاختر تأثيراً عند الضرب:\n(يمكنك اختيار أكثر من تأثير)", reply_markup=kb_effects())
    return S_ITEM_EFFECTS

async def cb_effects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data == "eff_done" or data == "eff_none":
        await query.edit_message_text(
            f"✅ التأثيرات: {user_data_store[uid].get('effects', []) or 'لا يوجد'}\n\nهل تريد إضافة وصفة للصنع؟",
            reply_markup=kb_recipe()
        )
        return S_ITEM_RECIPE_Q

    eff = data.replace("eff_", "")
    effects = user_data_store[uid].get("effects", [])
    if eff not in effects:
        effects.append(eff)
    user_data_store[uid]["effects"] = effects
    await query.edit_message_text(
        f"✅ تمت إضافة: {eff}\nالتأثيرات الحالية: {effects}\n\nاختر تأثيراً آخر أو اضغط انتهيت:",
        reply_markup=kb_effects()
    )
    return S_ITEM_EFFECTS

async def cb_recipe_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "recipe_no":
        user_data_store[uid]["has_recipe"] = False
        await query.edit_message_text("اكتب namespace الخاص بك (مثال: mymod) أو اكتب skip للافتراضي:")
        return S_ITEM_NAMESPACE

    user_data_store[uid]["has_recipe"] = True
    await query.edit_message_text("اختر نوع الوصفة:", reply_markup=kb_recipe_type())
    return S_ITEM_RECIPE_TYPE

async def cb_recipe_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    recipe_type = query.data.replace("recipe_", "")
    user_data_store[uid]["recipe_type"] = recipe_type

    if recipe_type == "furnace":
        await query.edit_message_text("اكتب اسم الخام (مثال: minecraft:iron_ore):")
    else:
        await query.edit_message_text(
            "اكتب المكونات مفصولة بفاصلة\n"
            "مثال: minecraft:diamond,minecraft:stick,minecraft:stick\n\n"
            "للوصفة الكاملة (3x3) اكتب 9 مكونات"
        )
    return S_ITEM_INGREDIENTS

async def msg_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    recipe_type = user_data_store[uid].get("recipe_type", "shaped")

    if recipe_type == "furnace":
        user_data_store[uid]["input_item"] = text
    else:
        ingredients = [i.strip() for i in text.split(",")]
        user_data_store[uid]["ingredients"] = ingredients

    await update.message.reply_text("اكتب namespace الخاص بك (مثال: mymod) أو اكتب skip:")
    return S_ITEM_NAMESPACE

async def msg_namespace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ns = update.message.text.strip()
    if ns.lower() == "skip" or not ns:
        ns = "mymod"
    user_data_store[uid]["namespace"] = ns

    d = user_data_store[uid]
    summary = (
        f"📋 ملخص المود:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"النوع: {d.get('item_type', '؟')}\n"
        f"الاسم: {d.get('display_name', '؟')}\n"
        f"الضرر: {d.get('damage', '-')}\n"
        f"المتانة: {d.get('durability', '-')}\n"
        f"التأثيرات: {d.get('effects', []) or 'لا يوجد'}\n"
        f"الوصفة: {'نعم' if d.get('has_recipe') else 'لا'}\n"
        f"Namespace: {ns}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"هل تريد إنشاء المود؟"
    )
    await update.message.reply_text(summary, reply_markup=kb_confirm())
    return S_CONFIRM


# ════════════════════════════════════════════════════════
#  FOOD FLOW
# ════════════════════════════════════════════════════════

async def cb_food_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    nutrition = int(query.data.replace("nut_", ""))
    user_data_store[uid]["nutrition"] = nutrition
    await query.edit_message_text(
        f"✅ الشبع: {nutrition}\n\nاختر تأثيرات الطعام:",
        reply_markup=kb_food_effects()
    )
    return S_FOOD_EFFECTS

async def cb_food_effects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data.replace("food_", "")

    if data == "done" or data == "none":
        user_data_store[uid]["namespace"] = "mymod"
        d = user_data_store[uid]
        summary = (
            f"📋 ملخص الطعام:\n"
            f"━━━━━━━━━━━━━━━\n"
            f"الاسم: {d.get('display_name')}\n"
            f"الشبع: {d.get('nutrition', 4)}\n"
            f"التأثيرات: {d.get('effects', []) or 'لا يوجد'}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"هل تريد إنشاء المود؟"
        )
        await query.edit_message_text(summary, reply_markup=kb_confirm())
        return S_CONFIRM

    effects = user_data_store[uid].get("effects", [])
    if data not in effects:
        effects.append(data)
    user_data_store[uid]["effects"] = effects
    await query.edit_message_text(
        f"✅ تأثير مضاف: {data}\nالتأثيرات: {effects}\n\nاختر المزيد أو اضغط انتهيت:",
        reply_markup=kb_food_effects()
    )
    return S_FOOD_EFFECTS


# ════════════════════════════════════════════════════════
#  ARMOR FLOW
# ════════════════════════════════════════════════════════

async def msg_armor_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()
    armor_id = name.lower().replace(" ", "_")
    armor_id = ''.join(c if c.isalnum() or c=='_' else '' for c in armor_id) or "custom_armor"
    user_data_store[uid]["armor_name"] = armor_id
    user_data_store[uid]["display_prefix"] = name
    await update.message.reply_text("اختر مستوى الحماية:", reply_markup=kb_armor_protection())
    return S_ARMOR_PROTECTION

async def cb_armor_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    prot = query.data.replace("prot_", "")
    user_data_store[uid]["protection"] = prot
    user_data_store[uid]["namespace"] = "mymod"
    user_data_store[uid]["pieces"] = ["helmet", "chestplate", "leggings", "boots"]

    d = user_data_store[uid]
    summary = (
        f"📋 ملخص الدرع:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"الاسم: {d.get('display_prefix')}\n"
        f"الحماية: {prot}\n"
        f"القطع: خوذة + صدرية + ساقية + حذاء\n"
        f"━━━━━━━━━━━━━━━\n"
        f"هل تريد إنشاء المود؟"
    )
    await query.edit_message_text(summary, reply_markup=kb_confirm())
    return S_CONFIRM


# ════════════════════════════════════════════════════════
#  ENTITY FLOW
# ════════════════════════════════════════════════════════

async def cb_entity_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    ent_type = query.data.replace("ent_", "")
    user_data_store[uid]["entity_type"] = ent_type
    await query.edit_message_text("اكتب اسم الكيان (مثال: تنين الجحيم):")
    return S_ENTITY_NAME

async def msg_entity_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()
    entity_id = name.lower().replace(" ", "_")
    entity_id = ''.join(c if c.isalnum() or c=='_' else '' for c in entity_id) or "custom_entity"
    user_data_store[uid]["display_name"] = name
    user_data_store[uid]["entity_id"] = entity_id
    await update.message.reply_text("اختر كمية الحياة:", reply_markup=kb_health())
    return S_ENTITY_HEALTH

async def cb_entity_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    hp = int(query.data.replace("hp_", ""))
    user_data_store[uid]["health"] = hp
    await query.edit_message_text(f"✅ الحياة: {hp}\n\nاختر قوة الضرر:", reply_markup=kb_damage())
    return S_ENTITY_DAMAGE

async def cb_entity_damage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    dmg = int(query.data.replace("dmg_", ""))
    user_data_store[uid]["damage"] = dmg
    await query.edit_message_text(f"✅ الضرر: {dmg}\n\nاختر السرعة:", reply_markup=kb_speed())
    return S_ENTITY_SPEED

async def cb_entity_speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    spd = float(query.data.replace("spd_", ""))
    user_data_store[uid]["speed"] = spd
    await query.edit_message_text(f"✅ السرعة: {spd}\n\nاختر لون بيضة الإنشاء:", reply_markup=kb_color())
    return S_ENTITY_COLOR

async def cb_entity_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    color = query.data.replace("col_", "")
    user_data_store[uid]["color1"] = color
    user_data_store[uid]["color2"] = "black"
    user_data_store[uid]["namespace"] = "mymod"
    user_data_store[uid]["drops"] = [
        {"item": "minecraft:bone", "weight": 1, "min": 0, "max": 2}
    ]

    d = user_data_store[uid]
    summary = (
        f"📋 ملخص الكيان:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"الاسم: {d.get('display_name')}\n"
        f"النوع: {d.get('entity_type')}\n"
        f"الحياة: {d.get('health')} ❤️\n"
        f"الضرر: {d.get('damage')}\n"
        f"السرعة: {d.get('speed')}\n"
        f"اللون: {color}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"هل تريد إنشاء المود؟"
    )
    await query.edit_message_text(summary, reply_markup=kb_confirm())
    return S_CONFIRM


# ════════════════════════════════════════════════════════
#  BUILD & SEND
# ════════════════════════════════════════════════════════

async def cb_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "confirm_no":
        await query.edit_message_text("تم الإلغاء. أرسل /start للبدء من جديد.")
        return ConversationHandler.END

    await query.edit_message_text("⚙️ جارٍ بناء المود...")

    d = user_data_store[uid]
    mod_type = d.get("mod_type", "item")

    try:
        files = {}

        if mod_type == "item":
            files = build_item(d)
            if d.get("has_recipe"):
                recipe_files = build_recipe(d)
                files.update(recipe_files)

        elif mod_type == "food":
            files = build_item(d)

        elif mod_type == "armor":
            files = build_armor(d)

        elif mod_type == "entity":
            files = build_entity(d)

        # ── فحص نهائي ──
        # توليد الصور التلقائية
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

        # ── بناء mcpack ──
        mcpack_path = _build_mcpack(files, d.get("display_name", "addon"))

        # ── تقرير الفحص ──
        await query.message.reply_text(validation.summary())

        # ── إرسال الملف ──
        file_list = "\n".join(f"• {p}" for p in files.keys() if files[p] is not None)
        caption = (
            f"📦 المود جاهز!\n\n"
            f"الملفات:\n{file_list}\n\n"
            f"افتح الملف لتثبيته في ماين كرافت ✅\n"
            f"فعّل Beta APIs في إعدادات العالم"
        )

        with open(mcpack_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=os.path.basename(mcpack_path),
                caption=caption
            )

        # إذا كان في وضع الحزمة — احفظ وارجع
        if d.get("in_bundle"):
            bundle_store.setdefault(uid, []).append(d.copy())
            count = len(bundle_store[uid])
            os.remove(mcpack_path)
            await query.edit_message_text(
                f"✅ تم إضافة *{d.get('display_name','مود')}* للحزمة!\n"
                f"الحزمة الآن تحتوي {count} مودات\n\n"
                f"أضف مزيداً أو أنشئ الحزمة:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚔️ آيتم", callback_data="badd_item"),
                     InlineKeyboardButton("🍖 طعام", callback_data="badd_food")],
                    [InlineKeyboardButton("🛡️ درع", callback_data="badd_armor"),
                     InlineKeyboardButton("🐉 كيان", callback_data="badd_entity")],
                    [InlineKeyboardButton("🏗️ إنشاء الحزمة الآن", callback_data="bundle_build")],
                ])
            )
            return S_BUNDLE_ADD

        # حفظ المود تلقائياً
        try:
            save_mod(uid, d)
        except Exception as save_err:
            log.warning(f"Save mod warning: {save_err}")

        os.remove(mcpack_path)
        await query.edit_message_text("✅ تم إنشاء المود بنجاح!\nتم حفظه تلقائياً — أرسل /mymods لعرض مودات")

    except Exception as e:
        log.error(f"Build error: {e}", exc_info=True)
        await query.edit_message_text(f"❌ خطأ في البناء:\n{str(e)[:300]}\n\nأرسل /start وحاول مجدداً.")

    return ConversationHandler.END


def _build_mcpack(files: dict, name: str) -> str:
    safe_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in name)[:30] or "addon"
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, f"{safe_name}.mcpack")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            if isinstance(content, bytes):
                zf.writestr(path, content)
            elif content is None:
                zf.writestr(path, b'')
            else:
                zf.writestr(path, json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8"))

    return out


# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════
#  MY MODS — حفظ واسترجاع المودات
# ════════════════════════════════════════════════════════

TYPE_EMOJI = {
    "item": "⚔️", "food": "🍖",
    "armor": "🛡️", "entity": "🐉"
}

async def cmd_mymods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض قائمة مودات المستخدم"""
    uid = update.effective_user.id
    mods = get_user_mods(uid)

    if not mods:
        await update.message.reply_text(
            "لا يوجد مودات محفوظة بعد!\n"
            "أرسل /start لصنع أول مود."
        )
        return

    text = f"📚 مودات المحفوظة ({len(mods)}):\n━━━━━━━━━━━━━━━\n"
    buttons = []

    for mod in mods[:10]:  # أول 10 مودات
        emoji = TYPE_EMOJI.get(mod["type"], "📦")
        text += f"{emoji} {mod['name']} — {mod['date']}\n"
        buttons.append([
            InlineKeyboardButton(f"📥 {mod['name']}", callback_data=f"mod_dl_{mod['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"mod_del_{mod['id']}"),
        ])

    if len(mods) > 10:
        text += f"\n... و {len(mods)-10} مودات أخرى"

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cb_mods_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار المودات"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data.startswith("mod_dl_"):
        # إعادة تحميل المود
        mod_id = int(data.replace("mod_dl_", ""))
        mod_data = get_mod_by_id(mod_id, uid)

        if not mod_data:
            await query.edit_message_text("❌ المود غير موجود!")
            return

        await query.edit_message_text(f"⚙️ جارٍ إعادة بناء {mod_data.get('display_name','المود')}...")

        try:
            mod_type = mod_data.get("mod_type", "item")
            if mod_type in ("item", "food"):
                files = build_item(mod_data)
                if mod_data.get("has_recipe"):
                    files.update(build_recipe(mod_data))
            elif mod_type == "armor":
                files = build_armor(mod_data)
            elif mod_type == "entity":
                files = build_entity(mod_data)
            else:
                files = build_item(mod_data)

            try:
                files.update(generate_all_textures(mod_data))
            except Exception as tex_err:
                log.warning(f"Texture: {tex_err}")

            mcpack_path = _build_mcpack(files, mod_data.get("display_name", "addon"))

            with open(mcpack_path, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(mcpack_path),
                    caption=f"📥 {mod_data.get('display_name','المود')} — تم إعادة التحميل"
                )
            os.remove(mcpack_path)
            await query.edit_message_text(f"✅ تم إرسال {mod_data.get('display_name','المود')}!")

        except Exception as e:
            await query.edit_message_text(f"❌ خطأ: {str(e)[:200]}")

    elif data.startswith("mod_del_"):
        # حذف المود
        mod_id = int(data.replace("mod_del_", ""))
        mod_data = get_mod_by_id(mod_id, uid)
        name = mod_data.get("display_name", "المود") if mod_data else "المود"

        await query.edit_message_text(
            f"هل تريد حذف *{name}*؟",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ نعم احذفه", callback_data=f"mod_confirm_del_{mod_id}"),
                 InlineKeyboardButton("❌ لا", callback_data="mod_cancel_del")],
            ])
        )

    elif data.startswith("mod_confirm_del_"):
        mod_id = int(data.replace("mod_confirm_del_", ""))
        deleted = delete_mod(mod_id, uid)
        if deleted:
            count = get_mods_count(uid)
            await query.edit_message_text(
                f"✅ تم الحذف!\n"
                f"المودات المتبقية: {count}\n\n"
                f"أرسل /mymods لعرض القائمة."
            )
        else:
            await query.edit_message_text("❌ لم يتم العثور على المود!")

    elif data == "mod_cancel_del":
        await query.edit_message_text("تم الإلغاء. أرسل /mymods للعودة للقائمة.")


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
            S_ITEM_NAMESPACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_namespace)],
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
            S_BUNDLE_MODE: [CallbackQueryHandler(cb_bundle_mode, pattern="^mode_")],
            S_BUNDLE_ADD: [CallbackQueryHandler(cb_bundle_add, pattern="^badd_|^bundle_")],
            S_BUNDLE_CONFIRM: [CallbackQueryHandler(cb_bundle_confirm, pattern="^bundle_")],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("mymods", cmd_mymods))
    app.add_handler(CallbackQueryHandler(cb_mods_actions, pattern="^mod_"))
    log.info("✅ البوت يعمل — بدون AI!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
