from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Дружба корпус 1 второй этаж")],
        [KeyboardButton(text="Я хочу сделать массаж")],
        [KeyboardButton(text="Я хочу получить массаж")],
        [KeyboardButton(text="Мои записи")],
        [KeyboardButton(text="Расписание кемпа «Трогай тут»")],
    ],
    resize_keyboard=True
)

reminder_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Я помню и приду 👌", callback_data="confirm")],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_reminder")],
    ]
)