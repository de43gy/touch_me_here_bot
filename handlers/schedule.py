from aiogram import types, Router, F
from aiogram.filters import Command
from keyboards import main_menu
from datetime import datetime
import logging
from utils import get_current_moscow_time, parse_slot_datetime

logger = logging.getLogger(__name__)

router = Router()

SCHEDULE_DATA = [
    {
        "date": "28 февраля",
        "events": [
            {"time": "16:00-17:00", "title": "Чайная церемония", "description": ""},
            {
                "time": "17:00-19:00",
                "title": "@Nastya_avacada мк-массаж \"Грани тактильности: 1001 способ расслабить котика\"",
                "description": """Поговорим про то, как:
- выбрать инструмент или технику 
- определить достаточное воздействие
- правильно прокоммуницировать с партнером (котиком) и настроить на контакт 
- оценить свои силы на контакт
- правильно завершить процесс
Попрактикуемся друг на друге
И конечно поделимся, что хотим унести со встречи себе"""
            },
            {"time": "19:00", "title": "Гостевой мк-массаж или чай", "description": ""},
            {"time": "20:00-21:00", "title": "Чайная церемония", "description": ""},
            {
                "time": "21:00-23:00",
                "title": "Тактильно-аромо иммерсив \"Хижина внутрь\"",
                "description": "Живая очередь"
            }
        ]
    },
    {
        "date": "01 марта",
        "events": [
            {"time": "12:00-13:00", "title": "Гостевой Мк (может не быть)", "description": ""},
            {"time": "13:00-14:00", "title": "Чайная церемония", "description": ""},
            {
                "time": "14:00-15:00",
                "title": "@AnnaVao Массаж ногами",
                "description": "Возьмите чистые носочки или полотенце, но если этого ничего нет, то не беда"
            },
            {"time": "15:00-16:00", "title": "Чайная церемония", "description": ""},
            {
                "time": "16:00-17:00",
                "title": "@olga_aga Психологическая практика \"Больше Любви\" 🤩",
                "description": """Эта психологическая практика о том, как оказаться в текущем моменте и заземлиться в нем. Мы будем соприкасаться с чувством любви, нежности и принятия, а также окружать себя этими прекрасными состояниями.
Техники, которые вы узнаете на этой практике можно будет забрать с собой как чудесный подарок и пользоваться ими когда это будет вам очень нужно"""
            },
            {"time": "17:00-18:00", "title": "Чайная церемония", "description": ""},
            {
                "time": "18:00-19:00",
                "title": "@vovachay \"Массаж лица кисточками\"",
                "description": ""
            },
            {
                "time": "19:00-21:00",
                "title": "\"Другой массаж\" от Алексея Алфёрова",
                "description": """Долго искал технику, соединяющую в себе такую эффективность, простоту и одновременно бесконечную глубину, на мк я приоткрою для вас эту дверцу 

Сочетаем элементы терапевтического тайского массажа по линии Дживака (врач семьи Будды Шакьямуни) и одного из современных направлений остеопатического массажа"""
            },
            {
                "time": "23:00-01:00",
                "title": "Тактильно-аромо иммерсив \"Хижина внутрь\"",
                "description": "Живая очередь"
            }
        ]
    },
    {
        "date": "02 марта",
        "events": [
            {"time": "12:00-13:00", "title": "Чайная церемония", "description": ""},
            {
                "time": "13:00-15:00",
                "title": "@Kristi_oleshko \"Трогательный тройничек\"",
                "description": "Интуитивный массаж в тройках"
            }
        ]
    }
]

def is_event_in_future(date_str, time_str):
    try:
        now = get_current_moscow_time()
        event_datetime = parse_slot_datetime(date_str, time_str)
        
        if not event_datetime:
            return False
            
        return event_datetime > now
    except Exception as e:
        logger.error(f"Ошибка при определении времени события: {e}")
        return True

@router.message(F.text == "Расписание кемпа «Трогай тут»")
async def show_schedule(message: types.Message):
    try:
        now = get_current_moscow_time()
        
        schedule_message = "📅 <b>Расписание кемпа «Трогай тут»</b>\n\n"
        has_future_events = False
        
        for day in SCHEDULE_DATA:
            date_str = day["date"]
            has_day_events = False
            day_message = f"<b>{date_str}</b>\n"
            
            for event in day["events"]:
                if is_event_in_future(date_str, event["time"]):
                    has_day_events = True
                    has_future_events = True
                    day_message += f"<b>{event['time']}</b>\n{event['title']}\n"
                    if event["description"]:
                        day_message += f"{event['description']}\n"
                    day_message += "\n"
            
            if has_day_events:
                schedule_message += day_message
        
        if not has_future_events:
            schedule_message += "К сожалению, все события уже прошли."
            
        await message.answer(schedule_message, parse_mode="HTML", reply_markup=main_menu)
        
    except Exception as e:
        logger.error(f"Ошибка при отображении расписания: {e}")
        await message.answer("Произошла ошибка при получении расписания. Пожалуйста, попробуйте позже.", reply_markup=main_menu)

@router.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    await show_schedule(message)