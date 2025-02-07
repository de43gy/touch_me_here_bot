from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Я хочу сделать массаж")],
        [KeyboardButton(text="Я хочу получить массаж")],
        [KeyboardButton(text="Мои записи")],
    ],
    resize_keyboard=True
)

reminder_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Я помню и приду 👌", callback_data="confirm")],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_reminder")],
    ]
)