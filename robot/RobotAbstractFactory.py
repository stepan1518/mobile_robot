from .RobotConnection import RobotConnection
from .Robot import Robot

CONNECTION_CONFIG = 'coppeliaSym.yml'
connection = None
robot = None

class RobotAbstractFactory:
    def __init__(self):
        pass

    @staticmethod
    def createConnection():
        global connection

        if connection == None:
            connection = RobotConnection(CONNECTION_CONFIG)

        return connection

    @staticmethod
    def createRobot():
        global robot

        if robot == None:
            robot = Robot(RobotAbstractFactory.createConnection())

        return robot