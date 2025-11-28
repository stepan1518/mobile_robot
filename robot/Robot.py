import sys
import numpy as np
import time

sys.path.append('./sim_lib')

try:
    import sim
except ImportError:
    print('Ошибка импорта библиотеки sim')
    exit()

class Robot:
    robotName = 'RobaBoba'
    target_point = 'roba_boba_point'
    connection = None
    distanceTreshHold = 0.21
    currentPosition = 'dummy_20'

    def __init__(self, connection):
        self.connection = connection

        res, point_handle = sim.simxGetObjectHandle(self.connection.getClientId(), self.target_point, sim.simx_opmode_blocking)
        sim.simxSetObjectPosition(self.connection.getClientId(), point_handle, -1, [0, 0, 0], sim.simx_opmode_blocking)

    def moveToPoint(self, pointName):
        res, point_handle = sim.simxGetObjectHandle(self.connection.getClientId(), self.target_point,
                                                    sim.simx_opmode_blocking)
        res, target_handle = sim.simxGetObjectHandle(self.connection.getClientId(), pointName, sim.simx_opmode_blocking)
        res_pos, pos = sim.simxGetObjectPosition(self.connection.getClientId(), target_handle, -1, sim.simx_opmode_blocking)
        sim.simxSetObjectPosition(self.connection.getClientId(), point_handle, -1, pos, sim.simx_opmode_blocking)

        current_position = pos
        distance = np.sqrt(np.array(current_position[:2]).dot(np.array(current_position[:2])))
        while distance > self.distanceTreshHold:
            time.sleep(5)

            _, robotHandle = sim.simxGetObjectHandle(self.connection.getClientId(), self.robotName, sim.simx_opmode_blocking)
            _, robot_position = sim.simxGetObjectPosition(self.connection.getClientId(), robotHandle, -1, sim.simx_opmode_blocking)
            _, target_handle = sim.simxGetObjectHandle(self.connection.getClientId(), self.target_point, sim.simx_opmode_blocking)
            _, current_position = sim.simxGetObjectPosition(self.connection.getClientId(), target_handle, -1, sim.simx_opmode_blocking)

            diff = np.array(robot_position[:2]) - np.array(current_position[:2])
            distance = np.sqrt(diff.dot(diff))

            print(robot_position, current_position)
            print(f'Distance : {distance}\n\n')

        self.currentPosition = pointName

        return pointName

    def getCurrentPosition(self):
        return self.currentPosition