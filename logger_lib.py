from datetime import datetime
import logging


class Schedule_bot_Logging:
    '''Класс, отвечающий за логирование. Логи пишутся в файл, так же выводятся в консоль'''
    def __init__(self):
        self.mylogs = logging.getLogger(__name__)
        self.mylogs.setLevel(logging.DEBUG)
        # обработчик записи в лог-файл
        self.name = 'log/' + \
            '-'.join('-'.join('-'.join(str(datetime.now()).split()
                                       ).split('.')).split(':')) + '.log'
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