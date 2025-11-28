import yaml
import sys

sys.path.append('./sim_lib')

try:
    import sim
except ImportError:
    print('Ошибка импорта библиотеки sim')
    exit()

class RobotConnection:

    clientID = -1

    def __init__(self, configFileName):
        # Загружаем конфигурацию из YAML-файла
        with open(f'./resources/{configFileName}', 'r') as file:
            config = yaml.safe_load(file)

        sim.simxFinish(-1)

        # Получаем параметры подключения
        connectionAddress = config['connection']['connectionAddress']
        connectionPort = config['connection']['connectionPort']
        waitUntilConnected = config['connection']['waitUntilConnected']
        doNotReconnectOnceDisconnected = config['connection']['doNotReconnectOnceDisconnected']
        timeOutInMs = config['connection']['timeOutInMs']
        commThreadCycleInMs = config['connection']['commThreadCycleInMs']

        self.clientID = sim.simxStart(connectionAddress, connectionPort, waitUntilConnected, doNotReconnectOnceDisconnected, timeOutInMs, commThreadCycleInMs)

        if self.clientID != -1:
            print('Подключение установлено')
        else:
            print('Ошибка подключения')

    def __del__(self):
        self.closeConnection()

    def closeConnection(self):
        sim.simxFinish(self.clientID)

    def getClientId(self):
        return self.clientID