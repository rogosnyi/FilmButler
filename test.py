import aiohttp
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TMDB_API_KEY
from keyboards import main_menu_buttons

class Form(StatesGroup):
    normal_search = State()
    recommendation = State()

async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вітаю! Мене звати FilmButler і я твій персональний помічник у пошуку фільмів! "
                         "Для початку обери один із варіантів нижче \U0000263A", reply_markup=main_menu_buttons())

async def message_handler(message: types.Message, state: FSMContext):
    if message.text == "Шукати фільм за назвою \U0001F50D":
        await state.set_state(Form.normal_search)
        await message.answer("Звісно! Напиши, будь-ласка, назву фільму котрий хочеш знайти.", reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "Фільми в тренді \U0001F4C8":
        await show_trending(message)
    elif message.text == "Порекомендуй фільм \U0001F914":
        await state.set_state(Form.recommendation)
        await message.answer("Добре, надай назву будь-якого фільму "
                             "і я створю для тебе список зі схожими кінострічками.", reply_markup=types.ReplyKeyboardRemove())
    #зміна префіксу для search_movies в залежності від стану
    else:
        current_state = await state.get_state()
        if current_state == Form.normal_search:
            await search_movies(message, state, callback_data_prefix="film_info")
        elif current_state == Form.recommendation:
            await search_movies(message, state, callback_data_prefix="recommend")

async def search_movies(message: types.Message, state: FSMContext, callback_data_prefix: str):
    film_name = message.text
    async with aiohttp.ClientSession() as session:
        url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={film_name}&language=uk-UA'
        async with session.get(url) as response:
            data = await response.json()
            if data['results']:
                inline_keyboard = []
                for film in data['results']:
                    title = film['title']
                    release_date = film['release_date'][:4] if 'release_date' in film and film['release_date'] else 'N/A'
                    inline_keyboard.append([InlineKeyboardButton(text=f"{title} - {release_date}", callback_data=f"{callback_data_prefix}:{film['id']}")])
                reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
                await message.answer("Ось результати пошуку. Будь-ласка, обери фільм котрий маєш наувазі:", reply_markup=reply_markup)
            else:
                await message.answer("Вибачте, але я не зміг знайти фільм за наданою назвою, спробуйте іншу \U0001F625", reply_markup=main_menu_buttons())

async def show_trending(message: types.Message):
    async with aiohttp.ClientSession() as session:
        url = f'https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}&language=uk-UA'
        async with session.get(url) as response:
            data = await response.json()
            if data['results']:
                inline_keyboard = []
                for movie in data['results']:
                    inline_keyboard.append([InlineKeyboardButton(text=movie['title'], callback_data=f"film_info:{movie['id']}")])
                reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
                await message.answer("Актуальні кіно-тренди:", reply_markup=reply_markup)

async def show_film_info(callback_query: CallbackQuery):
    film_id = callback_query.data.split(":")[1]
    async with aiohttp.ClientSession() as session:
        url = f'https://api.themoviedb.org/3/movie/{film_id}?api_key={TMDB_API_KEY}&append_to_response=videos&language=uk-UA'
        async with session.get(url) as response:
            film = await response.json()
            genres = ", ".join([genre['name'] for genre in film['genres']])
            title = film['title']
            overview = film['overview']
            release_date = film['release_date']
            poster_path = film['poster_path']
            ratings = round(film['vote_average'], 1)
            poster_url = f'https://image.tmdb.org/t/p/w500{poster_path}'

            trailer_url = None
            for video in film.get('videos', {}).get('results', []):
                if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                    trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
                    break

            # If no trailer is found in Ukrainian, fetch the trailer in English
            if not trailer_url:
                url_en = f'https://api.themoviedb.org/3/movie/{film_id}?api_key={TMDB_API_KEY}&append_to_response=videos&language=en-US'
                async with session.get(url_en) as response_en:
                    film_en = await response_en.json()
                    for video in film_en.get('videos', {}).get('results', []):
                        if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                            trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
                            break

            caption = f"Назва фільму: {title}\n\nЖанри: {genres}\n\nСинапсис: {overview}\n\nРейтинг фільму: {ratings}/10 \U00002B50\n\nДата виходу: {release_date}"
            if trailer_url:
                caption += f"\n\n[Дивитись трейлер]({trailer_url})"

            if poster_url:
                try:
                    await callback_query.message.answer_photo(photo=poster_url, caption=caption, parse_mode='Markdown',
                                                              reply_markup=main_menu_buttons())
                except Exception as e:
                    await callback_query.message.answer(caption, parse_mode='Markdown',
                                                        reply_markup=main_menu_buttons())
            else:
                await callback_query.message.answer(caption, parse_mode='Markdown', reply_markup=main_menu_buttons())

    await callback_query.answer()

async def show_recommendations(callback_query: CallbackQuery):
    film_id = callback_query.data.split(":")[1]
    await callback_query.message.delete()  # Delete the message with the movie list
    async with aiohttp.ClientSession() as session:
        recommendations_url = f'https://api.themoviedb.org/3/movie/{film_id}/recommendations?api_key={TMDB_API_KEY}&language=uk-UA'
        async with session.get(recommendations_url) as rec_response:
            rec_data = await rec_response.json()
            if rec_data['results']:
                url = f'https://api.themoviedb.org/3/movie/{film_id}?api_key={TMDB_API_KEY}&language=uk-UA'
                async with session.get(url) as film_response:
                    film = await film_response.json()
                    title = film['title']

                inline_keyboard = []
                for rec_film in rec_data['results']:
                    inline_keyboard.append([InlineKeyboardButton(text=rec_film['title'], callback_data=f"film_info:{rec_film['id']}")])
                reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
                await callback_query.message.answer(f"Якщо тобі подобається {title}, я рекомендую подивитись:", reply_markup=reply_markup)
            else:
                await callback_query.message.answer("Вибач, але я не зміг створити список рекомендацій за цим фільмом.", reply_markup=main_menu_buttons())

def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command(commands=["start"]))
    dp.message.register(message_handler)
    dp.callback_query.register(show_film_info, lambda callback_query: callback_query.data.startswith("film_info"))
    dp.callback_query.register(show_recommendations, lambda callback_query: callback_query.data.startswith("recommend"))
