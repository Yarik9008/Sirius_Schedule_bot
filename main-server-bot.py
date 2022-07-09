import telebot
import logging
from datetime import datetime
from lorettOrbital.orbital import *

TOKEN = '5560587670:AAGyi76WNfR1QAilZosAuSLv6m_9SCGKYvI'
LON = 39.96655
LAT = 43.40013
HEIGHT = 0.01
'''
sudo pip3 install pyTelegramBotAPI
sudo pip3 install LorettOrbital 

scheduleapt - Request schedule apt 
schedule - Request schedule l
updatetle - Update tle data
'''


class Neboscope_Logging:
    '''Класс отвечающий за логирование. Логи пишуться в файл, так же выводться в консоль'''

    def __init__(self):
        self.mylogs = logging.getLogger(__name__)
        self.mylogs.setLevel(logging.DEBUG)
        # обработчик записи в лог-файл
        self.name = 'log/' + \
            '-'.join('-'.join('-'.join(str(datetime.now()).split()
                                       ).split('.')).split(':')) + 'log'
        self.file = logging.FileHandler(self.name)
        self.fileformat = logging.Formatter(
            "%(asctime)s:%(levelname)s:%(message)s")
        self.file.setLevel(logging.DEBUG)
        self.file.setFormatter(self.fileformat)
        # обработчик вывода в консоль лог файла
        self.stream = logging.StreamHandler()
        self.streamformat = logging.Formatter(
            "%(levelname)s:%(module)s:%(message)s")
        self.stream.setLevel(logging.DEBUG)
        self.stream.setFormatter(self.streamformat)
        # инициализация обработчиков
        self.mylogs.addHandler(self.file)
        self.mylogs.addHandler(self.stream)
        #coloredlogs.install(level=logging.DEBUG, logger=self.mylogs, fmt='%(asctime)s [%(levelname)s] - %(message)s')

        self.mylogs.info('start-logging-sistem')

    def debug(self, message):
        '''сообщения отладочного уровня'''
        self.mylogs.debug(message)

    def info(self, message):
        '''сообщения информационного уровня'''
        self.mylogs.info(message)

    def warning(self, message):
        '''не критичные ошибки'''
        self.mylogs.warning(message)

    def critical(self, message):
        self.mylogs.critical(message)

    def error(self, message):
        self.mylogs.error(message)


### init ###
# логирование
logger = Neboscope_Logging()
try:
    bot = telebot.TeleBot(TOKEN)
    logger.info('init telegram bot')
except:
    logger.warning('no init telegram bot')

# работа с библиотекой для рассчета пролетов

config = supportedStationTypes['r8s'].copy()
config['horizon'] = 10      # минимальная высота для приема
    # Игнорировать вполеты, максимальная точка которых ниже
config['minApogee'] = 35
    #                    Название  Широта   Долгота  Высота в км     часовой пояс
station = Scheduler("r8s", LAT, LON, HEIGHT, timeZone=3, config=config)

logger.info('init orbital')


# Комманда '/schedule'
@bot.message_handler(commands=['schedule'])
def neo_start(message):
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    bot.send_message(message.chat.id, station.getSchedule(24, returnTable=True))

# Комманда '/updateTle'


@bot.message_handler(commands=['updatetle'])
def neo_start(message):
    logger.debug(f'User: {message.from_user.username} Data: {message.text}')
    check = station.update()
    bot.send_message(message.chat.id, f'Tle update data: {check}')


bot.infinity_polling()
