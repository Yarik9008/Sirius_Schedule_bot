from lorettOrbital.orbital import *
from pprint import pprint


if __name__ == '__main__':
    config = supportedStationTypes['r8s'].copy()
    config['horizon'] = 30      # минимальная высота для приема
    config['minApogee'] = 40    # Игнорировать вполеты, максимальная точка которых ниже

    #                    Название  Широта   Долгота  Высота в км     часовой пояс
    station = Scheduler("r8sTest", 55.6442, 37.3325, 0.159,          timeZone=3,      config=config)

    # Проверяем актуальность tle
    station.update()
    
    # Получить координаты по интернету !НЕ ТОЧНО ОЧЕНЬ!
    #station.setCoordinates(*station.getCoordinatesByIp())

    # Выводим текущие настройки станции
    pprint(station.getStation(), indent=3)
    print()

    # Выводим расписание      сколько часов возвращать ли таблицу   Сохранять расписание в файл (сохраняет расписание рядом с собой)
    print(station.getSchedule(12,           returnTable=True,       saveSchedule=True))

    # рассчитать ближайший пролет (сохраняет трек-файл рядом с собой)
    station.nextPass()

