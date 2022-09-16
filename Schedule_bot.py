from telebot.async_telebot import AsyncTeleBot
from logger_lib import Schedule_bot_Logging
from lorettOrbital.orbital import *
from datetime import datetime
from telebot import types
from pathlib import Path
import multiprocessing
import sqlite3 as sql
import configparser
import schedule
import asyncio
import time


'''
sudo pip3 install pyTelegramBotAPI
sudo pip3 install LorettOrbital 

'''

# Инициализация необходимых переменных
# Токен целевого бота
orig_TOKEN = '5560587670:AAGyi76WNfR1QAilZosAuSLv6m_9SCGKYvI'
# Токен тестового бота
TOKEN = '5203174377:AAHphu6MLlOLeY09KVKBNI_f6R278_03Cvo'
# Стандартные координаты
LON = 39.96655
LAT = 43.40013
HEIGHT = 0.01
# Поддержваемы библиотекой типы станций
sST = supportedStationTypes
# Инициализация логгера
logger = Schedule_bot_Logging()
# Буфер значений
temp_coords, temp_codename = '', ''
# Пути к бд
stations_db_path = Path.cwd() / 'databases' / 'stations.db'
users_db_path = Path.cwd() / 'databases' / 'users.db'
# Флаг первичной настройки для пользователя
first_set = False
# Инициализация бота
try:
    bot = AsyncTeleBot(TOKEN)
    logger.info('init telegram bot')
except Exception as e:
    logger.warning(f'telegram bot is not initialized: {e}')
# Инициализация объекта станции
#                    station_codename, latitude, longitude, height, timezone
station = Scheduler("r8s",              LAT,        LON,    HEIGHT, timeZone=3)
logger.info('init orbital')


# Функция обновления конфигов из библиотеки и tle-файлов
def auto_update():
    global stations_db_path
    try:
        tle_update_check = station.update()
        if tle_update_check:
            logger.info('tle updated')
    except Exception as e:
        logger.error('tle have not been updated:' + str(e))
    try:
        # headers: band = 'bandtype', focus(~) = float, horizon = int, kinematic = 'kinematictype',
        #          minApogee = int, radius(~) = float, sampleRate = float, satList = 'sat1;sat2;sat3'
        stations_db_connection = sql.connect(stations_db_path)
        stations_cursor = stations_db_connection.cursor()
        stations_cursor.execute("DELETE FROM Lorett_config")
        stations_db_connection.commit()
        lex = ('lex', sST['apt']['band'], '', sST['apt']['horizon'], sST['apt']['kinematic'], sST['apt']['minApogee'], '', sST['apt']['sampleRate'], ';'.join(sST['apt']['satList']))
        r8s = ('r8s', sST['r8s']['band'], '', sST['r8s']['horizon'], sST['r8s']['kinematic'], sST['r8s']['minApogee'], '', sST['r8s']['sampleRate'], ';'.join(sST['r8s']['satList']))
        c4s = ('c4s', sST['c4s']['band'], sST['c4s']['focus'], sST['c4s']['horizon'], sST['c4s']['kinematic'], sST['c4s']['minApogee'], sST['c4s']['radius'], sST['c4s']['sampleRate'], ';'.join(sST['c4s']['satList']))
        l2s = ('l2s', sST['l2s']['band'], sST['l2s']['focus'], sST['l2s']['horizon'], sST['l2s']['kinematic'], sST['l2s']['minApogee'], sST['l2s']['radius'], sST['l2s']['sampleRate'], ';'.join(sST['apt']['satList']))
        stations_db_connection.commit()
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", lex)
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", c4s)
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", l2s)
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", r8s)
        stations_db_connection.commit()
        stations_db_connection.close()
    except Exception as e:
        logger.error('station original configs not updated' + ':' + str(e))


# Функция выполнения по расписанию в отдельном потоке multiprocessing функции обновления данных auto_update
def update_data():
    try:
        schedule.every().day.at('00:00').do(auto_update)
        # schedule.every().day.at('00:00').do(notif_update)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logger.error('error in update_data: ' + str(e))


# Функция получения геолокации
@bot.message_handler(content_types=['location'])
async def location(message):
    global temp_coords, users_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        if message.location is not None:
            temp_coords = [message.location.latitude, message.location.longitude]
            await bot.send_message(message.chat.id,
                                    "Введите название, высоту над уровнем моря и временной пояс для текущей локации.\nПример: название: Москва, 0.01, 3",
                                    reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logger.error('error in /location: ' + str(e))


# Функция запуска и настройки бота
@bot.message_handler(commands=['start'])
async def start(message):
    global first_set
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        user_data = [elem[0] for elem in users_cursor.execute("SELECT user_id FROM users").fetchall()]
        geo_keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
        geo_keyboard.add(types.KeyboardButton(text="Отправить местоположение", request_location=True))
        if message.chat.id not in user_data:
            first_set = True
            users_cursor.execute(f"INSERT INTO users VALUES({message.chat.id},0,1,'r8s',0,3)")
            users_db_connection.commit()
            await bot.send_message(message.chat.id,
                                    "Доброго времени суток. Вас приветствует бот расчёта расписания пролётов спутников. Где Вы находитесь?",
                                    reply_markup=geo_keyboard)
        else:
            first_set = False
            notifications, use_default, current_station, current_location, timezone = users_cursor.execute(f"SELECT notifications, use_default, current_station, current_location, timezone FROM users WHERE user_id = {message.chat.id}").fetchone()
            if notifications == 0:
                notifications = 'Уведомления выключены'
            elif notifications == 1:
                notifications = 'Уведомления включены'
            if use_default == 1:
                use_default = 'Используется конфигурация станций от компании Lorett'
            elif use_default == 0:
                use_default = 'Используется пользовательская конфигурация станций'
            current_location += ' ' + ', '.join(list(map(str, list(users_cursor.execute(f"SELECT latitude, longitude, height FROM locations WHERE user_id = {message.chat.id} AND codename = '{current_location}'").fetchone())))) + ', ' + f'UTC +{timezone}'
            if notifications and use_default and current_location and current_station:
                everything_fine = 'возможен'
            else:
                everything_fine = 'не возможен'
            await bot.send_message(message.chat.id,
                                    f"Доброго времени суток. Актуальная конфигурация:\n{notifications}\n{use_default}\nСтанция для расчетов: {current_station}\nМестоположение для расчетов: {current_location}\nРасчет пролётов спутников(/schedule) {everything_fine}.", 
                                    reply_markup=types.ReplyKeyboardRemove())
        users_db_connection.close()
    except Exception as e:
        logger.error('error in /start: ' + str(e))


# Проверка связи
@bot.message_handler(commands=['echo'])
async def echo(message):
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        await bot.send_message(message.chat.id,
                                "i'm alive!",
                                reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logger.error('error in /echo: ' + str(e))


# Функция мануального обновления конфигурации станций из библиотеки
@bot.message_handler(commands=['update_lorett_configs'])
async def lorett_config_updater(message):
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        stations_db_connection = sql.connect(stations_db_path)
        stations_cursor = stations_db_connection.cursor()
        stations_cursor.execute("DELETE FROM Lorett_config")
        stations_db_connection.commit()
        lex = ('lex', sST['apt']['band'], '', sST['apt']['horizon'], sST['apt']['kinematic'], sST['apt']['minApogee'], '', sST['apt']['sampleRate'], ';'.join(sST['apt']['satList']))
        r8s = ('r8s', sST['r8s']['band'], '', sST['r8s']['horizon'], sST['r8s']['kinematic'], sST['r8s']['minApogee'], '', sST['r8s']['sampleRate'], ';'.join(sST['r8s']['satList']))
        c4s = ('c4s', sST['c4s']['band'], sST['c4s']['focus'], sST['c4s']['horizon'], sST['c4s']['kinematic'], sST['c4s']['minApogee'], sST['c4s']['radius'], sST['c4s']['sampleRate'], ';'.join(sST['c4s']['satList']))
        l2s = ('l2s', sST['l2s']['band'], sST['l2s']['focus'], sST['l2s']['horizon'], sST['l2s']['kinematic'], sST['l2s']['minApogee'], sST['l2s']['radius'], sST['l2s']['sampleRate'], ';'.join(sST['apt']['satList']))
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", lex)
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", c4s)
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", l2s)
        stations_cursor.execute("INSERT INTO Lorett_config VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", r8s)
        stations_db_connection.commit()
        stations_db_connection.close()
        await bot.send_message(message.chat.id,
                                "Конфигурация станций, предоставляемая компанией Lorett, обновлена.",
                                reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        logger.error('error in /lorett_config_updater: ' + str(e))


# Функция включения уведомлений о пролетах
@bot.message_handler(commands=['turn_on_notifications'])
async def turn_on_notifications(message):
    global users_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        if users_cursor.execute(f"SELECT notifications FROM users WHERE user_id = {message.chat.id}").fetchone() != 1:
            users_cursor.execute(f"UPDATE users SET notifications = 1 WHERE user_id = {message.chat.id}")
            users_db_connection.commit()
            await bot.send_message(message.chat.id,
                                    'Уведомления о пролетах включены.',
                                    reply_markup=types.ReplyKeyboardRemove())
        users_db_connection.close()
    except Exception as e:
        logger.error('error in /turn_on_notifications: ' + str(e))


# Функция выключения уведомлений о пролетах
@bot.message_handler(commands=['turn_off_notifications'])
async def turn_off_notifications(message):
    global users_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        if users_cursor.execute(f"SELECT notifications FROM users WHERE user_id = {message.chat.id}").fetchone() != 0:
            users_cursor.execute(f"UPDATE users SET notifications = 0 WHERE user_id = {message.chat.id}")
            await bot.send_message(message.chat.id,
                                    'Уведомления о пролетах выключены.',
                                    reply_markup=types.ReplyKeyboardRemove())
        users_db_connection.commit()
        users_db_connection.close()
    except Exception as e:
        logger.error('error in /turn_off_notifications: ' + str(e))


# Функция смены конфигов станций на конфиги, предоставляемые компанией
@bot.message_handler(commands=['use_lorett_station_config'])
async def use_Lorett_station_config(message):
    global users_db_path, stations_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        stations_db_connection = sql.connect(stations_db_path)
        stations_cursor = stations_db_connection.cursor()
        if users_cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone() != 1:
            users_cursor.execute(f"UPDATE users SET use_default = 1 WHERE user_id = {message.chat.id}")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            stations = [elem[0] for elem in stations_cursor.execute(f"SELECT station_codename FROM Lorett_config").fetchall()]
            for station in stations:
                markup.add(types.KeyboardButton(station))
            await bot.send_message(message.chat.id,
                                    'Используется конфигурация станций компании Лоретт. Выберите станцию для расчетов:',
                                    reply_markup=markup)
        users_db_connection.commit()
        users_db_connection.close()
        stations_db_connection.commit()
        stations_db_connection.close()
    except Exception as e:
        logger.error('error in /use_Lorett_station_configs: ' + str(e))


# Функция смены конфигов станций на пользовательские
@bot.message_handler(commands=['use_user_station_config'])
async def use_user_station_config(message):
    global users_db_path, stations_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        stations_db_connection = sql.connect(stations_db_path)
        stations_cursor = stations_db_connection.cursor()
        if users_cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone() != 0:
            users_cursor.execute(f"UPDATE users SET use_default = 0 WHERE user_id = {message.chat.id}")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            stations = [elem[0] for elem in stations_cursor.execute(f"SELECT station_codename FROM user_configs WHERE user_id = {message.chat.id}").fetchall()]
            for station in stations:
                markup.add(types.KeyboardButton(station))
            await bot.send_message(message.chat.id,
                                    'Используется пользовательская конфигурация станций.',
                                    reply_markup=markup)
        users_db_connection.commit()
        users_db_connection.close()
        stations_db_connection.commit()
        stations_db_connection.close()
    except Exception as e:
        logger.error('error in /use_user_station_config: ' + str(e))


# Функция расчета расписания
@bot.message_handler(commands=['schedule'])
async def get_schedule(message):
    global station, users_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        use_default, current_station, current_location, timezone = users_cursor.execute(f"SELECT use_default, current_station, current_location, timezone FROM users WHERE user_id = {message.chat.id}").fetchone()
        current_location_coords = users_cursor.execute(f"SELECT latitude, longitude, height FROM locations WHERE user_id = {message.chat.id} AND codename = '{current_location}'").fetchone()
        if current_station == 'lex':
            station = Scheduler('apt', *current_location_coords, timeZone=int(timezone))
        else:
            station = Scheduler(current_station, *current_location_coords, timeZone=int(timezone))
        current_schedule = station.getSchedule(24, returnTable=True)
        if use_default == 1:
            # разделение расписания
            current_schedule = f'generated with Lorett configs\nstation:{current_station}\n\n' + current_schedule
        else:
            current_schedule = f'generated with user configs\nstation:{current_station}\n\n' + current_schedule
        if len(current_schedule) <= 4096:
            await bot.send_message(message.chat.id,
                                    current_schedule,
                                    reply_markup=types.ReplyKeyboardRemove())
        else:
            filename = str(datetime.now()).split(' ')
            filename = filename[0].replace('-', '') + '_' + filename[1].split('.')[0].replace(':', '') + '-' + current_station + '_' + current_location + '.txt' 
            filename = str(Path.cwd() / 'log' / filename)
            with open(filename, 'w') as schedule_file:
                schedule_file.write(current_schedule)
            with open(filename, 'rb') as schedule_file:
                schedule_data = schedule_file.read()
            await bot.send_document(message.chat.id,
                                    schedule_data,
                                    visible_file_name=filename,
                                    caption='Размер сообщения превышает допустимый, расписание помещено в файл.')
        users_db_connection.close()
    except Exception as e:
        logger.error('error in /schedule: ' + str(e))


# Функция помощи страдающим
@bot.message_handler(commands=['help'])
async def help(message):
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    await bot.send_message(message.chat.id,
                            '''СТАРОЕпри первом запуске, бот просит кинуть локацию и назвать ее. дальше - команды:
/schedule - расчет расписания для стандартных параметров ('r8s', координаты как в сочи были, конфиги оригинальные от Лоретт, без уведомлений)
/turn_on_notifications - включить уведомления
/turn_off_notifications - выключить уведомления
/use_Lorett_station_config - использовать оригинальные конфиги станций из библиотеки
/use_user_station_config - использовать пользовательские конфиги станций
/echo - простой чек, жив\мертв бот

смена станции для расчетов осуществляется просто написанием названия станции боту, например: 'c4s' -> Станция для расчетов успешно изменена"
смена \ добавление новой локации осуществляется написанием боту строки формата "локация: название, широта, долгота, высота" -> "локация успешно изменена \ добавлена)"''')


# Функция получения списка сохраненных локаций
@bot.message_handler(commands=['get_saved_locations_list'])
async def get_saved_locations_list(message):
    global users_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    users_db_connection = sql.connect(users_db_path)
    users_cursor = users_db_connection.cursor()
    saved_locations = list(map(lambda x: ', '.join(list(map(str, x))), [elem[1:] for elem in users_cursor.execute(f"SELECT * FROM locations WHERE user_id = {message.chat.id}").fetchall()]))
    saved_locations = '\n'.join(saved_locations)
    users_db_connection.close()
    await bot.send_message(message.chat.id,
                            saved_locations)


# Функция изменения пользовательских конфигов из файла, присланного боту
@bot.message_handler(content_types=['document'])
async def config_changer(message):
    global stations_db_path
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    try:
        # проверка на соответствие расширения присланного файла
        file_info = await bot.get_file(message.document.file_id)
        if '.ini' in file_info.file_path:
            downloaded_file = await bot.download_file(file_info.file_path)
            user_station_config_path = Path.cwd() / 'user_station_config.ini'
            with open(user_station_config_path, 'wb') as config_file:
                config_file.write(downloaded_file)
            config = configparser.ConfigParser()
            config.read(user_station_config_path)
            # махинации с бд
            headers = ['station_codename', 'band', 'focus', 'horizon', 'kinematic', 'minApogee', 'radius', 'sampleRate', 'satList']
            stations_db_connection = sql.connect(stations_db_path)
            stations_cursor = stations_db_connection.cursor()
            stations_cursor.execute(f"DELETE FROM user_configs WHERE user_id = {message.chat.id}")
            stations_db_connection.commit()
            for section in config.sections():
                temp_string = [message.chat.id]
                for header in headers:
                    if header in config[section]:
                        temp_string.append(config[section][header])
                    else:
                        temp_string.append('')
                temp_string = tuple(temp_string)
                stations_cursor.execute("INSERT INTO user_configs VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", temp_string)
            stations_db_connection.commit()
            stations_db_connection.close()
            await bot.reply_to(message,
                                "Файл конфигурации изменён.")
        else:
            await bot.reply_to(message,
                                "Неверный формат файла. Требуемый формат: *.ini")
    except Exception as e:
        logger.error('error in configuration updating from .ini file: ' + str(e))


# Функция обработки текста сообщений
@bot.message_handler(content_types=['text'])
async def text_getter(message):
    global station, stations_db_path, users_db_path, first_set
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    if message.text is not None:
        users_db_connection = sql.connect(users_db_path)
        users_cursor = users_db_connection.cursor()
        stations_db_connection = sql.connect(stations_db_path)
        stations_cursor = stations_db_connection.cursor()
        if users_cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone()[0] == 1:
            tablename = 'Lorett_config'
        else:
            tablename = 'user_configs'
        if 'название:' in message.text.lower():
            try:
                global temp_coords, temp_codename
                temp_codename, temp_height, temp_timezone = message.text.split(':')[-1].strip().split(', ')
                users_cursor.execute(f"INSERT INTO locations VALUES(?, ?, ?, ?, ?)", (message.chat.id, temp_codename, *list(map(float, temp_coords)), float(temp_height)))
                users_cursor.execute(f"UPDATE users SET current_location = '{temp_codename}' WHERE user_id = {message.chat.id}")
                users_cursor.execute(f"UPDATE users SET timezone = '{temp_timezone}' WHERE user_id = {message.chat.id}")
                users_db_connection.commit()
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                if users_cursor.execute(f"SELECT use_default FROM users WHERE user_id = {message.chat.id}").fetchone() == 0:
                    stations = [elem[0] for elem in stations_cursor.execute(f"SELECT station_codename FROM user_configs WHERE user_id = {message.chat.id}").fetchall()]
                else:
                    stations = [elem[0] for elem in stations_cursor.execute(f"SELECT station_codename FROM Lorett_config").fetchall()]
                for station in stations:
                    markup.add(types.KeyboardButton(station))
                await bot.send_message(message.chat.id,
                                        f"Локация '{temp_codename}' успешно сохранена.\nВыберите станцию для расчёта пролетов:",
                                        reply_markup=markup)
            except Exception as e:
                logger.error('error in /text,название: ' + str(e))
        elif message.text in [elem[0] for elem in users_cursor.execute(f"SELECT codename FROM locations WHERE user_id = {message.chat.id}").fetchall()]:
            try:
                users_cursor.execute(f"UPDATE users SET current_location = '{message.text}' WHERE user_id = {message.chat.id}")
                users_db_connection.commit()
                await bot.send_message(message.chat.id,
                                        f"Местоположение для расчётов изменено на {message.text.lower()}.",
                                        reply_markup=types.ReplyKeyboardRemove())
            except Exception as e:
                logger.error('error in /text,смена локации чисто названием: ' + str(e))
        elif message.text.lower() in [elem[0] for elem in stations_cursor.execute(f"SELECT station_codename FROM {tablename}").fetchall()]:
            try:
                users_cursor.execute(f"UPDATE users SET current_station = '{message.text.lower()}' WHERE user_id = {message.chat.id}")
                users_db_connection.commit()
                current_coords = users_cursor.execute(f"SELECT latitude, longitude, height FROM locations WHERE codename = (SELECT current_location FROM users WHERE user_id = {message.chat.id})").fetchone()
                current_timezone = users_cursor.execute(f"SELECT timezone FROM users WHERE user_id = {message.chat.id}").fetchone()
                await bot.send_message(message.chat.id,
                                        f"Станция для расчётов изменена на {message.text.lower()}.",
                                        reply_markup=types.ReplyKeyboardRemove())
                if first_set:
                    await bot.send_message(message.chat.id,
                                            f"/turn_on_notifications - включить уведомения о пролетах(временно недоступно)\n/turn_off_notifications - выключить уведомения о пролетах(временно недоступно)\n/use_lorett_station_config - использовать конфигурацию станций Lorett\n/use_user_station_config - использовать пользовательскую конфигурацию станций\n/schedule - рассчитать расписание пролётов",
                                            reply_markup=types.ReplyKeyboardRemove())
            except Exception as e:
                logger.error('error in /text,смена станции: ' + str(e))
        elif 'локация:' in message.text.lower():
            try:
                location_data = message.text.split(', ')
                location_name, location_coords = location_data[0].split(': ')[1], (location_data[1], location_data[2], float(location_data[3]))
                codenames = users_cursor.execute(f"SELECT * FROM locations WHERE user_id = {message.chat.id}").fetchall()
                if location_name not in [elem[1] for elem in codenames]:
                    users_cursor.execute("INSERT INTO locations VALUES(?, ?, ?, ?, ?)", (message.chat.id, location_name, *location_coords))
                    users_db_connection.commit()
                    await bot.send_message(message.chat.id,
                                            f"Локация для расчётов добавлена и текущая изменена на {location_name}.",
                                            reply_markup=types.ReplyKeyboardRemove())
                    station = Scheduler(users_cursor.execute(f"SELECT current_station FROM users WHERE user_id = {message.chat.id}").fetchone()[0], *location_coords, timeZone=3)
                else:
                    await bot.send_message(message.chat.id,
                                            f"Локация для расчётов изменена на {location_name}.",
                                            reply_markup=types.ReplyKeyboardRemove())
                    station = Scheduler(users_cursor.execute(f"SELECT current_station FROM users WHERE user_id = {message.chat.id}").fetchone()[0], *location_coords, timeZone=3)
            except Exception as e:
                logger.error('error in /text,локация: ' + str(e))
        users_db_connection.close()
        stations_db_connection.close()
    else:
        await bot.send_message(message.chat.id,
                                'А сообщение-то пустое',
                                reply_markup=types.ReplyKeyboardRemove())
                    


if __name__ == '__main__':
    try:
        multiprocessing.set_start_method('spawn')
        schedule_process = multiprocessing.Process(target=update_data)
        schedule_process.start()
        asyncio.run(bot.infinity_polling(request_timeout=3600))
    except Exception as e:
        logger.error('error in main start: ' + str(e))
