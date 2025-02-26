from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu, reminder_menu
from database import get_available_slots, book_slot, get_slot_by_id
from utils import format_slot_info, is_slot_available, get_current_moscow_time, parse_slot_datetime, normalize_time_format
from datetime import datetime, timedelta
import asyncio
import logging
import pytz

from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

class ReceiveMassage(StatesGroup):
    confirmation = State()
    day = State()
    time = State()
    comment = State()

router = Router()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    await callback_query.message.answer("Вы вернулись в главное меню", reply_markup=main_menu)
    
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")

@router.message(F.text == "/debug_time")
async def debug_time(message: types.Message):
    try:
        now_utc = datetime.now(pytz.UTC)
        now_moscow = get_current_moscow_time()
        
        result = "Отладка времени:\n\n"
        result += f"UTC: {now_utc}\n"
        result += f"Московское время: {now_moscow}\n"
        result += f"Разница: {now_moscow.tzinfo.utcoffset(now_moscow)}\n\n"
        
        import aiosqlite
        from config import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT * FROM slots WHERE status = 'active'")
            rows = await cursor.fetchall()
            
            if not rows:
                result += "Нет активных слотов в базе данных."
            else:
                columns = [description[0] for description in cursor.description]
                result += "Активные слоты:\n\n"
                
                for row in rows:
                    slot = dict(zip(columns, row))
                    time_value = slot['time']
                    normalized_time = normalize_time_format(time_value)
                    slot_datetime = parse_slot_datetime(slot['day'], time_value)
                    
                    result += f"ID: {slot['id']}\n"
                    result += f"День: {slot['day']}\n"
                    result += f"Время (исх.): {time_value}\n"
                    result += f"Время (норм.): {normalized_time}\n"
                    result += f"Парсированная дата/время: {slot_datetime}\n"
                    result += f"В будущем: {slot_datetime > now_moscow}\n"
                    result += f"Giver ID: {slot['giver_id']}\n"
                    result += f"Receiver ID: {slot['receiver_id']}\n\n"
                    
        await message.answer(result)
    except Exception as e:
        logger.error(f"Ошибка при отладке времени: {e}")
        await message.answer(f"Ошибка при отладке: {e}")

@router.message(F.text == "Я хочу получить массаж")
async def show_rules(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Я прочитал и согласен", callback_data="confirm_receive_rules")]
    ])
    
    await message.answer(
        "«Важно!\n"
        "При дарении массажа необходимо соблюдать принципы взаимного согласия и уважения. "
        "Все действия должны быть комфортными для обеих сторон. Массаж не подразумевает никакого "
        "сексуализированного контекста. Если кто-либо испытывает дискомфорт, процесс должен быть "
        "немедленно остановлен. Уважайте границы друг друга!»",
        reply_markup=markup
    )
    await state.set_state(ReceiveMassage.confirmation)

@router.callback_query(ReceiveMassage.confirmation, F.data == "confirm_receive_rules")
async def show_available_slots_after_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    slots = await get_available_slots()
    if not slots:
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            "К сожалению, сейчас нет доступных слотов для записи.", 
            reply_markup=inline_markup
        )
        await state.clear()
        return

    user_id = callback_query.from_user.id
    
    now = get_current_moscow_time()
    logger.info(f"Текущее московское время: {now}")
    
    logger.info(f"Доступные слоты: {len(slots)}")
    for i, slot in enumerate(slots):
        logger.info(f"Слот {i+1}: день={slot.get('day', 'Н/Д')}, время={slot.get('time', 'Н/Д')}")
    
    filtered_slots = []
    for slot in slots:
        try:
            if 'day' not in slot or 'time' not in slot:
                logger.error(f"Слот не содержит необходимых полей day или time: {slot}")
                continue
                
            day_str = slot['day']
            if not day_str or len(day_str.split()) < 2:
                logger.error(f"Некорректный формат дня: {day_str}")
                continue
            
            day_parts = day_str.split()
            if day_parts[0] == 'День':
                logger.error(f"Некорректный формат дня (начинается с 'День'): {day_str}")
                continue
            
            normalized_time = normalize_time_format(slot['time'])
            logger.info(f"Нормализованное время слота: {normalized_time} (исходное: {slot['time']})")
              
            slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
            
            is_future = slot_datetime and slot_datetime > now
            logger.info(f"Слот в будущем: {is_future}, datetime={slot_datetime}")
            
            if not is_future:
                logger.info(f"Пропущен прошедший слот: {slot['day']} {slot['time']}")
                continue
                
            is_not_self = slot['giver_id'] != user_id
            logger.info(f"Слот не создан текущим пользователем: {is_not_self}, giver_id={slot['giver_id']}, user_id={user_id}")
            
            if not is_not_self:
                logger.info(f"Пропущен собственный слот: {slot['day']} {slot['time']}")
                continue
                
            receiver_id = slot['receiver_id']
            if receiver_id is not None:
                logger.info(f"Пропущен занятый слот: {slot['day']} {slot['time']}, receiver_id={receiver_id}")
                continue
                
            has_conflicts = not await is_slot_available(slot['day'], slot['time'], user_id)
            logger.info(f"Слот имеет конфликты: {has_conflicts}")
            
            if has_conflicts:
                logger.info(f"Пропущен конфликтующий слот: {slot['day']} {slot['time']}")
                continue
            
            filtered_slots.append(slot)
            logger.info(f"Добавлен доступный слот: {slot['day']} {slot['time']}")
        except Exception as e:
            logger.error(f"Ошибка при фильтрации слота: {e}")
    
    if not filtered_slots:
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            "К сожалению, все доступные слоты уже прошли или заняты.", 
            reply_markup=inline_markup
        )
        await state.clear()
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    days = sorted(list(set([slot['day'] for slot in filtered_slots])))

    for day in days:
        button = types.InlineKeyboardButton(text=day, callback_data=f"receive_day:{day}")
        markup.inline_keyboard.append([button])

    await callback_query.message.edit_text("Выберите день:", reply_markup=markup)
    await state.set_state(ReceiveMassage.day)

@router.callback_query(ReceiveMassage.day)
async def process_day_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    if callback_query.data.startswith("receive_day:"):
        day = callback_query.data.split(":")[1]
        await state.update_data(day=day)

        slots = await get_available_slots()
        now = get_current_moscow_time()
        
        day_slots = []
        for slot in slots:
            if slot['day'] == day:
                try:
                    slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
                    
                    if slot_datetime and slot_datetime > now:
                        day_slots.append(slot)
                except Exception as e:
                    logger.error(f"Ошибка при фильтрации слота по дню: {e}")
        
        user_id = callback_query.from_user.id
        
        filtered_slots = []
        for slot in day_slots:
            if slot['giver_id'] != user_id and slot['receiver_id'] is None and await is_slot_available(slot['day'], slot['time'], user_id):
                filtered_slots.append(slot)
        
        if not filtered_slots:
            await callback_query.message.edit_text(
                f"К сожалению, на день {day} нет доступных слотов или все слоты уже заняты.",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="← Назад", callback_data="back_to_days")
                ]])
            )
            return

        markup = types.InlineKeyboardMarkup(inline_keyboard=[])
        for slot in filtered_slots:
            slot_info = await format_slot_info(slot)
            button = types.InlineKeyboardButton(text=slot_info, callback_data=f"receive_time:{slot['id']}")
            markup.inline_keyboard.append([button])
        
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text="← Назад", callback_data="back_to_days")
        ])

        await callback_query.message.edit_text(
            f"Доступные слоты на {day}:\n\n"
            f"«Вы можете делать массаж и меньше часа, просто укажите это в комментарии. \n"
            f"Пожалуйста не опаздывайте на свой слот получения массажа 🙏🏻»", 
            reply_markup=markup
        )
        await state.set_state(ReceiveMassage.time)
    elif callback_query.data == "back_to_days":
        await back_to_days(callback_query, state)

@router.callback_query(ReceiveMassage.day, F.data == "back_to_days")
async def back_to_days(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Я прочитал и согласен", callback_data="confirm_receive_rules")]
    ])
    
    await callback_query.message.edit_text(
        "«Важно!\n"
        "При дарении массажа необходимо соблюдать принципы взаимного согласия и уважения. "
        "Все действия должны быть комфортными для обеих сторон. Массаж не подразумевает никакого "
        "сексуализированного контекста. Если кто-либо испытывает дискомфорт, процесс должен быть "
        "немедленно остановлен. Уважайте границы друг друга!»",
        reply_markup=markup
    )
    await state.set_state(ReceiveMassage.confirmation)

@router.callback_query(ReceiveMassage.time, F.data == "back_to_days")
async def back_to_days_from_time(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await back_to_days(callback_query, state)

@router.callback_query(ReceiveMassage.time)
async def process_time_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    if callback_query.data == "back_to_days":
        await back_to_days_from_time(callback_query, state)
        return
    elif callback_query.data.startswith("receive_time:"):   
        slot_id = int(callback_query.data.split(":")[1])
        await state.update_data(slot_id=slot_id)

        await callback_query.message.edit_text("Напишите комментарий к записи (необязательно):")
        await state.set_state(ReceiveMassage.comment)

@router.message(ReceiveMassage.comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text else ""
    data = await state.get_data()
    slot_id = data.get("slot_id")
    user_id = message.from_user.id

    slot = await get_slot_by_id(slot_id)
    if not slot:
        await message.answer("Извините, слот был занят или удален.", reply_markup=main_menu)
        await state.clear()
        return
        
    if slot['receiver_id'] is not None:
        await message.answer("Извините, этот слот уже занят другим пользователем.", reply_markup=main_menu)
        await state.clear()
        return
        
    if slot['giver_id'] == user_id:
        await message.answer("Извините, вы не можете записаться на собственный слот массажа.", reply_markup=main_menu)
        await state.clear()
        return
        
    if not await is_slot_available(slot['day'], slot['time'], user_id):
        await message.answer(
            "У вас уже есть запись на это время. Пожалуйста, выберите другое время.",
            reply_markup=main_menu
        )
        await state.clear()
        return
    
    try:
        now = get_current_moscow_time()
        slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
        
        if not slot_datetime or slot_datetime <= now:
            await message.answer("Извините, этот слот уже прошел.", reply_markup=main_menu)
            await state.clear()
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке времени слота: {e}")

    await book_slot(slot_id, user_id, comment)
    
    time_str = slot['time']
    if "-" in time_str:
        start_time, end_time = time_str.split("-")
        if ":" not in start_time.strip():
            start_time = f"{start_time.strip()}:00"
        if ":" not in end_time.strip():
            end_time = f"{end_time.strip()}:00"
        display_time = f"{start_time.strip()}-{end_time.strip()}"
    elif ":" not in time_str:
        display_time = f"{time_str}:00"
    else:
        display_time = time_str
        
    formatted_slot_info = await format_slot_info(slot)
    await message.answer(f"Вы записаны на получение массажа!\n{formatted_slot_info}\nВремя: {display_time}", reply_markup=main_menu)
    
    giver_id = slot['giver_id']
    await bot.send_message(giver_id, f"К вам записались на массаж!\nДень: {slot['day']}\nВремя: {display_time}\nКомментарий: {comment}")
    
    try:
        now = get_current_moscow_time()
        slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
        
        if not slot_datetime:
            logger.error(f"Не удалось распарсить дату/время слота: {slot['day']} {slot['time']}")
            await message.answer("Извините, произошла ошибка при обработке времени слота.", reply_markup=main_menu)
            await state.clear()
            return
            
        reminder_time = slot_datetime - timedelta(minutes=30)
        delay = (reminder_time - now).total_seconds()

        if delay > 0:
            asyncio.create_task(schedule_reminder(message.from_user.id, message.from_user.username, slot['day'], slot['time'], "receiver", delay))
        else:
            logger.warning(f"Пропущено напоминание для пользователя {message.from_user.username} (ID: {message.from_user.id}), время: {slot['day']} {slot['time']}")
    except Exception as e:
        logger.error(f"Ошибка при создании напоминания: {e}")
        
    await state.clear()

async def schedule_reminder(user_id: int, username: str, day: str, time: str, role: str, delay: int):
    await asyncio.sleep(delay)
    
    display_time = time
    if "-" in time:
        start_time, end_time = time.split("-")
        if ":" not in start_time.strip():
            start_time = f"{start_time.strip()}:00"
        if ":" not in end_time.strip():
            end_time = f"{end_time.strip()}:00"
        display_time = f"{start_time.strip()}-{end_time.strip()}"
    elif ":" not in time:
        display_time = f"{time}:00"
    
    if role == "giver":
        text = f"Я помню, что через 30 минут делаю массаж в «Трогай тут (корпус , этаж)» ({day}, {display_time}) и приду его делать 👌🏻"
    elif role == "receiver":
        text = f"Я помню, что через 30 минут получаю массаж в «Трогай тут (корпус , этаж)» ({day}, {display_time}) и приду его получать 👌🏻"
    await bot.send_message(user_id, text, reply_markup=reminder_menu)