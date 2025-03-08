import logging
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load grocery items from CSV
GROCERY_DATA = {}
CATEGORY_ORDER = []

def load_grocery_data():
    global GROCERY_DATA, CATEGORY_ORDER
    GROCERY_DATA = {}
    CATEGORY_ORDER = []

    with open('grocery_list.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        for row in reader:
            category, item, *quantities = row
            if category not in GROCERY_DATA:
                GROCERY_DATA[category] = []
                CATEGORY_ORDER.append(category)  # Maintain category order
            GROCERY_DATA[category].append((item, quantities))

load_grocery_data()

# Store user-selected items
USER_LISTS = {}

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    USER_LISTS[user_id] = {"month": None, "year": None, "items": {cat: [] for cat in GROCERY_DATA}}

    keyboard = [
        [InlineKeyboardButton(str(year), callback_data=f"year_{year}") for year in range(2025, 2030)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a year:", reply_markup=reply_markup)

def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.message.chat_id
    data = query.data

    if data.startswith("year_"):
        year = data.split("_")[1]
        USER_LISTS[user_id]["year"] = year
        keyboard = [
            [InlineKeyboardButton(month, callback_data=f"month_{month}")] for month in 
            ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text("Choose a month:", reply_markup=reply_markup)

    elif data.startswith("month_"):
        month = data.split("_")[1]
        USER_LISTS[user_id]["month"] = month
        send_category_menu(update, context, user_id)

    elif data.startswith("category_"):
        category = data.split("_")[1]
        send_item_menu(update, context, user_id, category)

    elif data.startswith("item_"):
        _, category, item = data.split("_", 2)
        send_quantity_menu(update, context, user_id, category, item)

    elif data.startswith("quantity_"):
        _, category, item, quantity = data.split("_", 3)
        if quantity == "Custom":
            context.user_data["awaiting_custom_quantity"] = (category, item)
            query.message.reply_text(f"Send custom quantity for {item}:")
        else:
            add_item_to_list(user_id, category, item, quantity)
            send_category_menu(update, context, user_id)

    elif data == "finish":
        send_final_list(update, context, user_id)

def send_category_menu(update: Update, context: CallbackContext, user_id: int):
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"category_{cat}")] for cat in CATEGORY_ORDER
    ]
    keyboard.append([InlineKeyboardButton("Finish List", callback_data="finish")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=user_id, text="Choose a category:", reply_markup=reply_markup)

def send_item_menu(update: Update, context: CallbackContext, user_id: int, category: str):
    keyboard = [
        [InlineKeyboardButton(item, callback_data=f"item_{category}_{item}")] for item, _ in GROCERY_DATA[category]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=user_id, text=f"Choose an item from {category}:", reply_markup=reply_markup)

def send_quantity_menu(update: Update, context: CallbackContext, user_id: int, category: str, item: str):
    quantities = next(q for i, q in GROCERY_DATA[category] if i == item)
    keyboard = [
        [InlineKeyboardButton(q, callback_data=f"quantity_{category}_{item}_{q}")] for q in quantities
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=user_id, text=f"Choose quantity for {item}:", reply_markup=reply_markup)

def add_item_to_list(user_id: int, category: str, item: str, quantity: str):
    USER_LISTS[user_id]["items"][category].append(f"{item} - {quantity}")

def send_final_list(update: Update, context: CallbackContext, user_id: int):
    grocery_list = f"Grocery list\t\t{update.effective_user.first_name}\t\t{USER_LISTS[user_id]['month']} {USER_LISTS[user_id]['year']}\n"
    grocery_list += "=" * 50 + "\n"

    for category in CATEGORY_ORDER:
        if USER_LISTS[user_id]["items"][category]:
            grocery_list += f"# {category}\n"
            for idx, item in enumerate(USER_LISTS[user_id]["items"][category], start=1):
                grocery_list += f"☐ {idx}. {item}\n"
            grocery_list += "\n"

    grocery_list += "=" * 50 + "\nTOTAL - \n"

    context.bot.send_message(chat_id=user_id, text=f"Your grocery list:\n\n{grocery_list}")

def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if "awaiting_custom_quantity" in context.user_data:
        category, item = context.user_data.pop("awaiting_custom_quantity")
        add_item_to_list(user_id, category, item, update.message.text)
        send_category_menu(update, context, user_id)

def main():
    updater = Updater("7747934303:AAHKO4Ei9_s8ucCHh5-xK66Pbp_DCIL7yVA", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    dp.add_handler(CommandHandler("done", send_final_list))
    dp.add_handler(CallbackQueryHandler(send_category_menu, pattern="^category_"))
    dp.add_handler(CommandHandler("text", handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
