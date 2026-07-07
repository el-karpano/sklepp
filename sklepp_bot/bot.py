# -*- coding: utf-8 -*-
import logging
import math
import threading
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

import database as db
from config import BOT_TOKEN, ADMIN_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)


async def noop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


def is_admin(user_id):
    return user_id == ADMIN_ID


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [
            InlineKeyboardButton("📂 Категории", callback_data="categories"),
            InlineKeyboardButton("📦 Товары", callback_data="all_products"),
        ],
    ])


def back_kb(cb="admin"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=cb)]])


async def _del(context, chat_id, msg_id):
    if msg_id:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass


async def _show_view(update, context, text, buttons, photo_url=None):
    query = update.callback_query
    chat_id = query.message.chat.id
    await _del(context, chat_id, context.user_data.pop("photo_msg_id", None))
    await _del(context, chat_id, context.user_data.pop("btn_msg_id", None))
    if photo_url:
        try:
            msg = await context.bot.send_photo(chat_id=chat_id, photo=photo_url)
            context.user_data["photo_msg_id"] = msg.message_id
        except Exception:
            pass
    msg = await context.bot.send_message(
        chat_id=chat_id, text=text,
        reply_markup=InlineKeyboardMarkup(buttons) if isinstance(buttons, list) else buttons,
        parse_mode="Markdown",
    )
    context.user_data["btn_msg_id"] = msg.message_id
    await query.answer()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    chat_id = update.message.chat.id
    for k in list(context.user_data):
        if k.endswith("_msg_id"):
            await _del(context, chat_id, context.user_data.pop(k))
    await update.message.reply_text(
        "🔧 *Панель управления* SKLEPP\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите раздел:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    await _show_view(update, context,
        "🔧 *Панель управления* SKLEPP\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите раздел:",
        main_menu_kb(),
    )


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    categories = await db.get_global_categories()
    all_products = await db.get_all_subcategories()
    product_count = len(all_products)
    total_value = sum(float(s.get("price_byn", 0) or 0) for s in all_products)
    text = (
        "📊 *Dashboard*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📂 Категории:    *{len(categories)}*\n"
        f"📦 Товаров:       *{product_count}*\n"
        f"💰 Оценка:       *{total_value:.2f}* BYN\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await _show_view(update, context, text, back_kb("admin"))


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    categories = await db.get_global_categories()
    all_products = await db.get_all_subcategories()
    sub_map = {}
    for s in all_products:
        cid = s["global_category_id"]
        sub_map.setdefault(cid, []).append(s)
    buttons = []
    for i, c in enumerate(categories, 1):
        subs = sub_map.get(c["id"], [])
        buttons.append([InlineKeyboardButton(
            f"{i}. {c['name']}  ({len(subs)} товаров)",
            callback_data=f"cat_{c['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="add_category")])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="admin")])
    text = "📂 *Категории*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    if not categories:
        text += "\n_Пока нет категорий_"
    await _show_view(update, context, text, buttons)


async def show_category_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    category_id = query.data.split("_", 1)[1]
    await _show_category_page(update, context, category_id, page=0)


async def show_category_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    parts = query.data.split("_")
    category_id = parts[2]
    page = int(parts[3])
    await _show_category_page(update, context, category_id, page)


async def _show_category_page(update, context, category_id, page):
    query = update.callback_query
    PAGE_SIZE = 50
    categories = await db.get_global_categories()
    category = next((c for c in categories if c["id"] == category_id), None)
    if not category:
        await query.answer("❌ Категория не найдена", show_alert=True)
        return
    subs = await db.get_subcategories(category_id)
    total = len(subs)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = subs[start:end]
    total_value = sum(float(s.get("price_byn", 0) or 0) for s in subs)
    buttons = []
    for s in page_items:
        buttons.append([InlineKeyboardButton(
            f"{s['name']}  •  {s.get('price_byn', 0)} BYN",
            callback_data=f"sub_{s['id']}"
        )])
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"catp_{category_id}_{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"catp_{category_id}_{page + 1}"))
    if total_pages > 1:
        buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("➕ Добавить товар", callback_data=f"add_sub_{category_id}")])
    buttons.append([
        InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_cat_{category_id}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"del_cat_{category_id}"),
    ])
    buttons.append([InlineKeyboardButton("◀️ К категориям", callback_data="categories")])
    text = (
        f"📂 *{category['name']}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Товаров: *{total}*\n"
        f"💰 Общая стоимость: *{total_value:.2f}* BYN\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if total_pages > 1:
        text += f"_Страница {page + 1} из {total_pages}_\n"
    if not subs:
        text += "\n_В этой категории пока нет товаров_"
    await _show_view(update, context, text, buttons, category.get("image_url"))


async def show_all_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    await _show_all_products_page(update, context, page=0)


async def show_all_products_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    page = int(query.data.split("_")[2])
    await _show_all_products_page(update, context, page)


async def _show_all_products_page(update, context, page):
    query = update.callback_query
    PAGE_SIZE = 50
    categories = await db.get_global_categories()
    all_products = await db.get_all_subcategories()
    cat_map = {c["id"]: c["name"] for c in categories}
    total = len(all_products)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = all_products[start:end]
    buttons = []
    for p in page_items:
        cat_name = cat_map.get(p["global_category_id"], "?")
        buttons.append([InlineKeyboardButton(
            f"{p['name']}  •  {p.get('price_byn', 0)} BYN  •  [{cat_name}]",
            callback_data=f"sub_{p['id']}"
        )])
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"allp_{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"allp_{page + 1}"))
    if total_pages > 1:
        buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="admin")])
    text = "📦 *Все товары*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    if total_pages > 1:
        text += f"_Страница {page + 1} из {total_pages}_\n"
    if not all_products:
        text += "\n_Пока нет товаров_"
    await _show_view(update, context, text, buttons)


async def show_subcategory_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    sub_id = query.data.split("_", 1)[1]
    sub = await db.get_subcategory(sub_id)
    if not sub:
        await query.answer("❌ Товар не найден", show_alert=True)
        return
    sub = sub[0]
    min_order = sub.get("min_order", 1) or 1
    text = (
        f"📦 *{sub['name']}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Цена: *{sub.get('price_byn', 0)}* BYN / *{sub.get('price_rub', 0)}* RUB\n"
        f"📦 Мин. заказ: *{min_order} шт.*\n"
        f"🕐 Добавлен: {str(sub.get('created_at', ''))[:10]}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = [
        [
            InlineKeyboardButton("✏️ Название", callback_data=f"edit_sub_name_{sub_id}"),
            InlineKeyboardButton("🖼 Фото", callback_data=f"edit_sub_photo_{sub_id}"),
        ],
        [
            InlineKeyboardButton("💰 BYN", callback_data=f"edit_sub_byn_{sub_id}"),
            InlineKeyboardButton("💰 RUB", callback_data=f"edit_sub_rub_{sub_id}"),
        ],
        [InlineKeyboardButton("📦 Мин. заказ", callback_data=f"edit_sub_moq_{sub_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"del_sub_{sub_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"cat_{sub['global_category_id']}")],
    ]
    await _show_view(update, context, text, buttons, sub.get("image_url"))


async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "add_cat_name"
    await query.edit_message_text(
        "➕ *Новая категория*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\nВведите название категории:",
        parse_mode="Markdown",
    )
    await query.answer()


async def edit_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    category_id = query.data.split("_", 2)[2]
    buttons = [
        [InlineKeyboardButton("✏️ Название", callback_data=f"edit_cat_name_{category_id}")],
        [InlineKeyboardButton("🖼 Фото", callback_data=f"edit_cat_photo_{category_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"cat_{category_id}")],
    ]
    await query.edit_message_text(
        "⚙️ *Редактирование категории*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\nЧто хотите изменить?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )
    await query.answer()


async def edit_category_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_cat_name"
    context.user_data["edit_cat_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("✏️ Введите новое название:")
    await query.answer()


async def edit_category_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_cat_photo"
    context.user_data["edit_cat_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("📸 Отправьте новое фото:")
    await query.answer()


async def delete_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    category_id = query.data.split("_", 2)[2]
    categories = await db.get_global_categories()
    category = next((c for c in categories if c["id"] == category_id), None)
    name = category["name"] if category else "???"
    subs = await db.get_subcategories(category_id)
    buttons = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"del_cat_yes_{category_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"cat_{category_id}")],
    ]
    await query.edit_message_text(
        f"⚠️ *Удаление категории*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Удалить *«{name}»* и *{len(subs)} товаров* внутри?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )
    await query.answer()


async def delete_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    category_id = query.data.split("_", 3)[3]
    await db.delete_global_category(category_id)
    await _show_view(update, context, "✅ Категория удалена!", main_menu_kb())


async def add_subcategory_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "add_sub_name"
    context.user_data["sub_global_cat_id"] = query.data.split("_", 2)[2]
    await query.edit_message_text(
        "➕ *Новый товар*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\nВведите название товара:",
        parse_mode="Markdown",
    )
    await query.answer()


async def edit_subcategory_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    sub_id = query.data.split("_", 2)[2]
    sub = await db.get_subcategory(sub_id)
    if not sub:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    sub = sub[0]
    buttons = [
        [
            InlineKeyboardButton("✏️ Название", callback_data=f"edit_sub_name_{sub_id}"),
            InlineKeyboardButton("🖼 Фото", callback_data=f"edit_sub_photo_{sub_id}"),
        ],
        [
            InlineKeyboardButton("💰 BYN", callback_data=f"edit_sub_byn_{sub_id}"),
            InlineKeyboardButton("💰 RUB", callback_data=f"edit_sub_rub_{sub_id}"),
        ],
        [InlineKeyboardButton("📦 Мин. заказ", callback_data=f"edit_sub_moq_{sub_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"sub_{sub_id}")],
    ]
    await query.edit_message_text(
        f"⚙️ *Редактирование: {sub['name']}*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\nЧто хотите изменить?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )
    await query.answer()


async def edit_sub_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_sub_name"
    context.user_data["edit_sub_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("✏️ Введите новое название:")
    await query.answer()


async def edit_sub_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_sub_photo"
    context.user_data["edit_sub_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("📸 Отправьте новое фото:")
    await query.answer()


async def edit_sub_byn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_sub_byn"
    context.user_data["edit_sub_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("💰 Введите новую цену BYN:")
    await query.answer()


async def edit_sub_rub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_sub_rub"
    context.user_data["edit_sub_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("💰 Введите новую цену RUB:")
    await query.answer()


async def edit_sub_moq_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "edit_sub_moq"
    context.user_data["edit_sub_id"] = query.data.split("_", 3)[3]
    await query.edit_message_text("📦 Введите минимальный заказ (шт.):")
    await query.answer()


async def delete_subcategory_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    sub_id = query.data.split("_", 2)[2]
    sub = await db.get_subcategory(sub_id)
    name = sub[0]["name"] if sub else "???"
    buttons = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"del_sub_yes_{sub_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"sub_{sub_id}")],
    ]
    await query.edit_message_text(
        f"⚠️ *Удаление товара*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Удалить *«{name}»*?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )
    await query.answer()


async def delete_subcategory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    sub_id = query.data.split("_", 3)[3]
    sub = await db.get_subcategory(sub_id)
    category_id = sub[0]["global_category_id"] if sub else None
    await db.delete_subcategory(sub_id)
    if category_id:
        await _show_view(update, context, "✅ Товар удалён!", back_kb(f"cat_{category_id}"))
    else:
        await _show_view(update, context, "✅ Товар удалён!", main_menu_kb())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    state = context.user_data.get("state")
    if not state:
        return
    chat_id = update.message.chat.id

    if state == "add_cat_name":
        context.user_data["cat_name"] = update.message.text
        context.user_data["state"] = "add_cat_photo"
        await update.message.reply_text("📸 Отправьте фото категории или /skip чтобы пропустить:")
        return

    if state == "edit_cat_name":
        await db.update_global_category(context.user_data["edit_cat_id"], name=update.message.text)
        await _clear_and_reply(context, chat_id, "✅ Название обновлено!", main_menu_kb())
        return

    if state == "add_sub_name":
        context.user_data["sub_name"] = update.message.text
        context.user_data["state"] = "add_sub_photo"
        await update.message.reply_text("📸 Отправьте фото товара или /skip:")
        return

    if state == "add_sub_byn":
        try:
            context.user_data["sub_byn"] = float(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число:")
            return
        context.user_data["state"] = "add_sub_rub"
        await update.message.reply_text("💰 Введите цену в RUB:")
        return

    if state == "add_sub_rub":
        try:
            context.user_data["sub_rub"] = float(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число:")
            return
        context.user_data["state"] = "add_sub_moq"
        await update.message.reply_text("📦 Минимальный заказ (шт.):")
        return

    if state == "add_sub_moq":
        try:
            moq = int(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите целое число:")
            return
        if moq < 1:
            await update.message.reply_text("⚠️ Минимум 1:")
            return
        d = dict(context.user_data)
        sub_name = d["sub_name"]
        await db.create_subcategory(
            global_category_id=d["sub_global_cat_id"], name=sub_name,
            image_url=d.get("sub_photo"), price_byn=d["sub_byn"],
            price_rub=d["sub_rub"], min_order=moq
        )
        await _clear_and_reply(context, chat_id, f"✅ Товар *'{sub_name}'* создан!", main_menu_kb())
        return

    if state == "edit_sub_name":
        await db.update_subcategory(context.user_data["edit_sub_id"], name=update.message.text)
        await _clear_and_reply(context, chat_id, "✅ Название обновлено!", main_menu_kb())
        return

    if state == "edit_sub_byn":
        try:
            price = float(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число:")
            return
        await db.update_subcategory(context.user_data["edit_sub_id"], price_byn=price)
        await _clear_and_reply(context, chat_id, "✅ Цена BYN обновлена!", main_menu_kb())
        return

    if state == "edit_sub_rub":
        try:
            price = float(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число:")
            return
        await db.update_subcategory(context.user_data["edit_sub_id"], price_rub=price)
        await _clear_and_reply(context, chat_id, "✅ Цена RUB обновлена!", main_menu_kb())
        return

    if state == "edit_sub_moq":
        try:
            moq = int(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите целое число:")
            return
        if moq < 1:
            await update.message.reply_text("⚠️ Минимум 1:")
            return
        await db.update_subcategory(context.user_data["edit_sub_id"], min_order=moq)
        await _clear_and_reply(context, chat_id, "✅ Мин. заказ обновлён!", main_menu_kb())
        return


async def _clear_and_reply(context, chat_id, text, kb):
    for k in list(context.user_data):
        if k.endswith("_msg_id"):
            await _del(context, chat_id, context.user_data.pop(k))
    for k in list(context.user_data):
        context.user_data.pop(k)
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="Markdown")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    state = context.user_data.get("state")
    if not state:
        return

    chat_id = update.message.chat.id
    telegram_file_id = update.message.photo[-1].file_id

    # Download photo from Telegram and upload to Supabase Storage
    try:
        file = await context.bot.get_file(telegram_file_id)
        file_bytes = await file.download_as_bytearray()
        file_name = f"{uuid.uuid4().hex}.jpg"
        photo_url = await db.upload_photo_to_storage(bytes(file_bytes), file_name)
        if not photo_url:
            await update.message.reply_text("❌ Ошибка загрузки фото в хранилище")
            return
    except Exception as e:
        logger.error(f"Photo upload error: {e}")
        await update.message.reply_text("❌ Ошибка загрузки фото")
        return

    if state == "add_cat_photo":
        cat_name = context.user_data.get("cat_name", "")
        await db.create_global_category(name=cat_name, image_url=photo_url)
        await _clear_and_reply(context, chat_id, f"✅ Категория *'{cat_name}'* создана!", main_menu_kb())
        return

    if state == "edit_cat_photo":
        await db.update_global_category(context.user_data["edit_cat_id"], image_url=photo_url)
        await _clear_and_reply(context, chat_id, "✅ Фото обновлено!", main_menu_kb())
        return

    if state == "add_sub_photo":
        context.user_data["sub_photo"] = photo_url
        context.user_data["state"] = "add_sub_byn"
        await update.message.reply_text("💰 Введите цену в BYN:")
        return

    if state == "edit_sub_photo":
        await db.update_subcategory(context.user_data["edit_sub_id"], image_url=photo_url)
        await _clear_and_reply(context, chat_id, "✅ Фото обновлено!", main_menu_kb())
        return


async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    state = context.user_data.get("state")
    if not state:
        return
    chat_id = update.message.chat.id

    if state == "add_cat_photo":
        cat_name = context.user_data.get("cat_name", "")
        await db.create_global_category(name=cat_name, image_url=None)
        await _clear_and_reply(context, chat_id, f"✅ Категория *'{cat_name}'* создана!", main_menu_kb())
        return

    if state == "add_sub_photo":
        context.user_data["sub_photo"] = None
        context.user_data["state"] = "add_sub_byn"
        await update.message.reply_text("💰 Введите цену в BYN:")
        return


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    chat_id = update.message.chat.id
    await _clear_and_reply(context, chat_id, "❌ Отменено.", main_menu_kb())


def main():
    from web import app as flask_app

    def run_web():
        flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    logger.info("Web server started on http://0.0.0.0:5000")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(CallbackQueryHandler(dashboard, pattern="^dashboard$"))
    app.add_handler(CallbackQueryHandler(noop_handler, pattern="^noop$"))
    app.add_handler(CallbackQueryHandler(show_all_products, pattern="^all_products$"))
    app.add_handler(CallbackQueryHandler(show_all_products_page, pattern=r"^allp_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(show_categories, pattern="^categories$"))

    app.add_handler(CallbackQueryHandler(add_category_start, pattern="^add_category$"))
    app.add_handler(CallbackQueryHandler(edit_category_name_start, pattern=r"^edit_cat_name_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_category_photo_start, pattern=r"^edit_cat_photo_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_category_start, pattern=r"^edit_cat_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(delete_category, pattern=r"^del_cat_yes_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(delete_category_confirm, pattern=r"^del_cat_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(show_category_page, pattern=r"^catp_[0-9a-f-]+_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(show_category_detail, pattern=r"^cat_[0-9a-f-]+$"))

    app.add_handler(CallbackQueryHandler(add_subcategory_start, pattern=r"^add_sub_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_sub_name_start, pattern=r"^edit_sub_name_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_sub_photo_start, pattern=r"^edit_sub_photo_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_sub_byn_start, pattern=r"^edit_sub_byn_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_sub_rub_start, pattern=r"^edit_sub_rub_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_sub_moq_start, pattern=r"^edit_sub_moq_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(edit_subcategory_start, pattern=r"^edit_sub_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(delete_subcategory, pattern=r"^del_sub_yes_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(delete_subcategory_confirm, pattern=r"^del_sub_[0-9a-f-]+$"))
    app.add_handler(CallbackQueryHandler(show_subcategory_detail, pattern=r"^sub_[0-9a-f-]+$"))

    app.add_handler(CallbackQueryHandler(admin_menu, pattern="^admin$"))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Regex("^/skip$"), handle_skip))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_error_handler(error_handler)

    app.run_polling()


if __name__ == "__main__":
    main()
