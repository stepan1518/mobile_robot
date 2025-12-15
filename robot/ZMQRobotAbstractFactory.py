import sys

from .ZMQRobot import ZMQRobot

sys.path.insert(0, '/home/steppp1518/Projects/mobile_robot/zmqRemoteApi/clients/python/src')

try:
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
except ImportError:
    print('Ошибка импорта библиотеки RemoteAPIClient')
    exit()

connection = None
robot = None

class ZMQRobotAbstractFactory:
    def __init__(self):
        pass

    @staticmethod
    def createConnection():
        global connection

        if connection == None:
            connection = RemoteAPIClient()

        return connection

    @staticmethod
    def createRobot():
        global robot

        if robot == None:
            robot = ZMQRobot(ZMQRobotAbstractFactory.createConnection())

        return robot