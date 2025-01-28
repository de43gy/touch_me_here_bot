from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("хочу сделать массаж"))
main_menu.add(KeyboardButton("хочу получить массаж"))
main_menu.add(KeyboardButton("Мои записи"))

reminder_menu = InlineKeyboardMarkup()
reminder_menu.add(InlineKeyboardButton("я помню и приду 👌", callback_data="confirm"))
reminder_menu.add(InlineKeybardButton("я передумал и не приду 🙅‍♂️", callback_data="cancel_reminder"))
