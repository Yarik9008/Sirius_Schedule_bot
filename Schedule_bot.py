from telebot.async_telebot import AsyncTeleBot
from logger_lib import Schedule_bot_Logging
from lorettOrbital.orbital import *
from telebot import types
import multiprocessing
import sqlite3 as sql
import schedule
import asyncio
import time


'''
sudo pip3 install pyTelegramBotAPI
sudo pip3 install LorettOrbital 

'''


TOKEN = '5560587670:AAGyi76WNfR1QAilZosAuSLv6m_9SCGKYvI'
debug_TOKEN = '5203174377:AAHphu6MLlOLeY09KVKBNI_f6R278_03Cvo'
LON = 39.96655
LAT = 43.40013
HEIGHT = 0.01
sST = supportedStationTypes
logger = Schedule_bot_Logging()
temp_coords, temp_codename = '', ''
try:
    bot = AsyncTeleBot(TOKEN)
    logger.info('init telegram bot')
except Exception as e:
    logger.warning(f'telegram bot is not initialized: {e}')
#                    Название  Широта   Долгота  Высота в км     часовой пояс
station = Scheduler("r8s", LAT, LON, HEIGHT, timeZone=3)
logger.info('init orbital')


# функция обновления данных
def auto_update():
    try:
        check = station.update()
        if check:
            logger.info('tle updated')
    except Exception as e:
        logger.error('tle not updated' + ':' + str(e))
    try:
        # headers: band = 'bandtype', focus(~) = float, horizon = int, kinematic = 'kinematictype',
        #          minApogee = int, radius(~) = float, sampleRate = float, satList = 'sat1;sat2;sat3'
        db_connection = sql.connect('databases/stations.db')
        cursor = db_connection.cursor()
        apt = ('apt', sST['apt']['band'], '', sST['apt']['horizon'], sST['apt']['kinematic'], sST['apt']['minApogee'], '', sST['apt']['sampleRate'], ';'.join(sST['apt']['satList']))
        r8s = ('r8s', sST['r8s']['band'], '', sST['r8s']['horizon'], sST['r8s']['kinematic'], sST['r8s']['minApogee'], '', sST['r8s']['sampleRate'], ';'.join(sST['r8s']['satList']))
        c4s = ('c4s', sST['c4s']['band'], sST['c4s']['focus'], sST['c4s']['horizon'], sST['c4s']['kinematic'], sST['c4s']['minApogee'], sST['c4s']['radius'], sST['c4s']['sampleRate'], ';'.join(sST['c4s']['satList']))
        l2s = ('l2s', sST['l2s']['band'], sST['l2s']['focus'], sST['l2s']['horizon'], sST['l2s']['kinematic'], sST['l2s']['minApogee'], sST['l2s']['radius'], sST['l2s']['sampleRate'], ';'.join(sST['apt']['satList']))
        cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", apt)
        cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", c4s)
        cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", l2s)
        cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", r8s)
        db_connection.commit()
        db_connection.close()
    except Exception as e:
        logger.error('station original configs not updated' + ':' + str(e))


# функция выполнения по расписанию в отдельном потоке multiprocessing
def update_data():
    try:
        schedule.every().day.at('00:00').do(auto_update)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logger.error('error in update_data: ' + str(e))


# функция получения геолокации
@bot.message_handler(content_types=['location'])
async def location(message):
    global temp_coords
    try:
        if message.location is not None:
            db_connection = sql.connect('databases/users.db')
            cursor = db_connection.cursor()
            cursor.execute(f"UPDATE users SET current_location = '{message.location.latitude};{message.location.longitude}' WHERE user_id = {message.chat.id}")
            db_connection.commit()
            db_connection.close()
            temp_coords = (message.location.latitude, message.location.longitude)
            await bot.send_message(message.chat.id, "Введите название локации. ('название: названиелокации')", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logger.error('error in /location: ' + str(e))


# функция запуска бота
@bot.message_handler(commands=['start'])
async def start(message):
    try:
        logger.debug(f'User: {message.from_user.username} Data: {message.text}')
        db_connection = sql.connect('databases/users.db')
        cursor = db_connection.cursor()
        user_data = [elem[0] for elem in cursor.execute("SELECT user_id FROM users").fetchall()]
        geo_keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
        button_geo = types.KeyboardButton(text="Отправить местоположение", request_location=True)
        geo_keyboard.add(button_geo)
        if message.chat.id not in user_data:
            cursor.execute(f"INSERT INTO users VALUES({message.chat.id},0,1,'r8s',0)")
            db_connection.commit()
            await bot.send_message(message.chat.id,
                                    "Доброго времени суток. Вас приветствует бот расчёта расписания пролётов спутников. Где Вы находитесь?",
                                    reply_markup=geo_keyboard)
        else:
            await bot.send_message(message.chat.id, "Доброго времени суток.", reply_markup=types.ReplyKeyboardRemove())
        db_connection.close()
    except Exception as e:
        logger.error('error in /start: ' + str(e))


# проверка связи
@bot.message_handler(commands=['echo'])
async def echo(message):
    try:
        logger.debug(f'User: {message.from_user.username} Data: {message.text}')
        await bot.send_message(message.chat.id, "i'm alive!", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logger.error('error in /schedule: ' + str(e))


# функция включения уведомлений
@bot.message_handler(commands=['turn_on_notifications'])
async def turn_on_notifications(message):
    try:
        db_connection = sql.connect('databases/users.db')
        cursor = db_connection.cursor()
        if cursor.execute(f"SELECT notifications FROM users WHERE user_id = {message.chat.id}").fetchone() != 1:
            cursor.execute(f"UPDATE users SET notifications = 1 WHERE user_id = {message.chat.id}")
            db_connection.commit()
            await bot.send_message(message.chat.id, 'Уведомления о пролетах включены.', reply_markup=types.ReplyKeyboardRemove())
        db_connection.close()
    except Exception as e:
        logger.error('error in /turn_on_notifications: ' + str(e))


# функция выключения уведомлений
@bot.message_handler(commands=['turn_off_notifications'])
async def turn_off_notifications(message):
    try:
        db_connection = sql.connect('databases/users.db')
        cursor = db_connection.cursor()
        if cursor.execute(f"SELECT notifications FROM users WHERE user_id = {message.chat.id}").fetchone() != 0:
            cursor.execute(f"UPDATE users SET notifications = 0 WHERE user_id = {message.chat.id}")
            await bot.send_message(message.chat.id, 'Уведомления о пролетах выключены.', reply_markup=types.ReplyKeyboardRemove())
        db_connection.commit()
        db_connection.close()
    except Exception as e:
        logger.error('error in /turn_off_notifications: ' + str(e))


# функция смены конфигов станций
@bot.message_handler(commands=['use_lorett_station_config'])
async def use_Lorett_station_config(message):
    try:
        db_connection = sql.connect('databases/users.db')
        cursor = db_connection.cursor()
        if cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone() != 1:
            cursor.execute(f"UPDATE users SET use_default = 1 WHERE user_id = {message.chat.id}")
            await bot.send_message(message.chat.id, 'Используется конфигурация станций компании Лоретт.', reply_markup=types.ReplyKeyboardRemove())
        db_connection.commit()
        db_connection.close()
    except Exception as e:
        logger.error('error in /use_Lorett_station_configs: ' + str(e))


# функция смены конфигов станций
@bot.message_handler(commands=['use_user_station_config'])
async def use_user_station_config(message):
    try:
        db_connection = sql.connect('databases/users.db')
        cursor = db_connection.cursor()
        if cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone() != 0:
            cursor.execute(f"UPDATE users SET use_default = 0 WHERE user_id = {message.chat.id}")
            await bot.send_message(message.chat.id, 'Используется пользовательская конфигурация станций.', reply_markup=types.ReplyKeyboardRemove())
        db_connection.commit()
        db_connection.close()
    except Exception as e:
        logger.error('error in /use_user_station_config: ' + str(e))


# функция расчета расписания
@bot.message_handler(commands=['schedule'])
async def get_schedule(message):
    global station
    try:
        db_connection = sql.connect('databases/users.db')
        cursor = db_connection.cursor()
        if cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone()[0] == 1:
            logger.debug(f'User: {message.from_user.username} Data: {message.text}')
            station_type = cursor.execute(f"SELECT current_station FROM users WHERE user_id = {message.chat.id}").fetchone()[0]
            station = Scheduler(station_type, LAT, LON, HEIGHT, timeZone=3)
            await bot.send_message(message.chat.id, f'generated with Lorett configs\nstation:{station_type}\n\n' + station.getSchedule(24, returnTable=True), reply_markup=types.ReplyKeyboardRemove())
        else:
            logger.debug(f'User: {message.from_user.username} Data: {message.text}')
            station_type = cursor.execute(f"SELECT current_station FROM users WHERE user_id = {message.chat.id}").fetchone()[0]
            station = Scheduler(station_type, LAT, LON, HEIGHT, timeZone=3)

            # config the station
            
            await bot.send_message(message.chat.id, f'generated with user configs\nstation:{station_type}\n\n' + station.getSchedule(24, returnTable=True), reply_markup=types.ReplyKeyboardRemove())
        db_connection.close()
    except Exception as e:
        logger.error('error in /schedule: ' + str(e))


# функция помощи страдающим
@bot.message_handler(commands=['help'])
async def help(message):
    await bot.send_message(message.chat.id, '''при первом запуске, бот просит кинуть локацию и назвать ее. дальше - команды:
/schedule - расчет расписания для стандартных параметров ('r8s', координаты как в сочи были, конфиги оригинальные от Лоретт, без уведомлений)
/turn_on_notifications - включить уведомления
/turn_off_notifications - выключить уведомления
/use_Lorett_station_config - использовать оригинальные конфиги станций из библиотеки
/use_user_station_config - использовать пользовательские конфиги станций
/echo - простой чек, жив\мертв бот

смена станции для расчетов осуществляется просто написанием названия станции боту, например: 'c4s' -> Станция для расчетов успешно изменена"
смена \ добавление новой локации осуществляется написанием боту строки формата "локация: название, широта, долгота, высота" -> "локация успешно изменена \ добавлена)"''')


# функция помощи страдающим
@bot.message_handler(commands=['get_saved_locations_list'])
async def get_saved_locations_list(message):
    db_connection = sql.connect('databases/users.db')
    cursor = db_connection.cursor()
    saved_locations = list(map(lambda x: ', '.join(list(map(str, x))), [elem[1:] for elem in cursor.execute(f"SELECT * FROM locations WHERE user_id = {message.chat.id}").fetchall()]))
    await bot.send_message(message.chat.id, saved_locations)


# функция обработки текста сообщений
@bot.message_handler(content_types=['text'])
async def text_getter(message):
    global LAT, LON, HEIGHT, station
    if message.text is not None:
        users_db_connection = sql.connect('databases/users.db')
        users_cursor = users_db_connection.cursor()
        stations_db_connection = sql.connect('databases/stations.db')
        stations_cursor = stations_db_connection.cursor()
        if users_cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone()[0] == 1:
            tablename = 'Lorett_config'
        else:
            tablename = 'user_config'
        if 'местоположение:' in message.text.lower():
            pass
        elif 'название:' in message.text.lower():
            try:
                global temp_coords, temp_codename
                temp_codename = message.text.lower().split(':')[-1].strip()
                users_cursor.execute(f"INSERT INTO locations VALUES(?, ?, ?, ?, ?)", (message.chat.id, temp_codename, *temp_coords, HEIGHT))
                users_db_connection.commit()
                await bot.send_message(message.chat.id, f"Локация {temp_codename} успешно сохранена.", reply_markup=types.ReplyKeyboardRemove())
            except Exception as e:
                logger.error('error in /text,название: ' + str(e))
                await bot.send_message(message.chat.id, f"Ошибка. {e}", reply_markup=types.ReplyKeyboardRemove())
        elif message.text in [elem[0] for elem in users_cursor.execute(f"SELECT codename FROM locations WHERE user_id = {message.chat.id}").fetchall()]:
            try:
                users_cursor.execute(f"UPDATE users SET current_location = '{message.text}' WHERE user_id = {message.chat.id}")
                LAT, LON, HEIGHT = users_cursor.execute(f"SELECT latitude, longitude, height FROM locations WHERE codename = '{message.text}'").fetchone()
                users_db_connection.commit()
                await bot.send_message(message.chat.id, f"Местоположение для расчётов изменено на {message.text.lower()}.", reply_markup=types.ReplyKeyboardRemove())
            except Exception as e:
                logger.error('error in /text,смена локации чисто названием: ' + str(e))
        elif message.text.lower() in [elem[0] for elem in stations_cursor.execute(f"SELECT station_codename FROM {tablename}").fetchall()]:
            try:
                users_cursor.execute(f"UPDATE users SET current_station = '{message.text.lower()}' WHERE user_id = {message.chat.id}")
                users_db_connection.commit()
                await bot.send_message(message.chat.id, f"Станция для расчётов изменена на {message.text.lower()}.", reply_markup=types.ReplyKeyboardRemove())
                station = Scheduler("r8s", LAT, LON, HEIGHT, timeZone=3)
            except Exception as e:
                logger.error('error in /text,смена станции: ' + str(e))
        elif 'локация:' in message.text.lower():
            try:
                location_data = message.text.split(', ')
                location_name, location_coords, HEIGHT = location_data[0].split(': ')[1], (location_data[1], location_data[2]), float(location_data[3])
                LAT, LON = list(map(float, location_coords))
                codenames = users_cursor.execute(f"SELECT * FROM locations WHERE user_id = {message.chat.id}").fetchall()
                if location_name not in [elem[1] for elem in codenames]:
                    users_cursor.execute("INSERT INTO locations VALUES(?, ?, ?, ?, ?)", (message.chat.id, location_name, LAT, LON, HEIGHT))
                    users_db_connection.commit()
                    await bot.send_message(message.chat.id, f"Локация для расчётов добавлена и текущая изменена на {location_name}.", reply_markup=types.ReplyKeyboardRemove())
                    station = Scheduler(users_cursor.execute(f"SELECT current_station FROM users WHERE user_id = {message.chat.id}").fetchone()[0], LAT, LON, HEIGHT, timeZone=3)
                else:
                    await bot.send_message(message.chat.id, f"Локация для расчётов изменена на {location_name}.", reply_markup=types.ReplyKeyboardRemove())
                    station = Scheduler(users_cursor.execute(f"SELECT current_station FROM users WHERE user_id = {message.chat.id}").fetchone()[0], LAT, LON, HEIGHT, timeZone=3)
            except Exception as e:
                logger.error('error in /text,локация: ' + str(e))
        users_db_connection.close()
        stations_db_connection.close()


if __name__ == '__main__':
    try:
        multiprocessing.set_start_method('spawn')
        schedule_process = multiprocessing.Process(target=update_data)
        schedule_process.start()
        asyncio.run(bot.infinity_polling())
    except Exception as e:
        logger.error('error in main start: ' + str(e))
