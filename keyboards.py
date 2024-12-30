from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_buttons():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Шукати фільм за назвою \U0001F50D")],
        [KeyboardButton(text="Фільми в тренді \U0001F4C8")],
        [KeyboardButton(text="Порекомендуй фільм \U0001F914")]
    ])
    return keyboard
