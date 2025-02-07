from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(F.text=="Я хочу сделать массаж")],
        [KeyboardButton(F.text=="Я хочу получить массаж")],
        [KeyboardButton(F.text=="Мои записи")],
    ],
    resize_keyboard=True
)

reminder_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(F.text=="Я помню и приду 👌", callback_data="confirm")],
        [InlineKeyboardButton(F.text=="Я передумал и не приду", callback_data="cancel_reminder")],
    ]
)



