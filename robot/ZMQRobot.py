import time
import numpy as np


class ZMQRobot:
    robotName = 'MobileRobot'
    target_point = 'roba_boba_point'
    floor = 'floor'
    connection = None
    distanceTreshHold = 0.31

    def __init__(self, connection):
        self.connection = connection
        self.sim = connection.getObject('sim')

        # Получаем хэндлы объектов
        self.robot_handle = self.sim.getObject(f'./{self.robotName}')
        self.target_handle = self.sim.getObject(f'./{self.target_point}')
        self.floor_handle = self.sim.getObject(f'./{self.floor}')

    def moveToPoint(self, point_handle):

        target_position = self.sim.getObjectPosition(point_handle, self.floor_handle)

        # Устанавливаем позицию целевой точки
        self.sim.setObjectPosition(self.target_handle, self.floor_handle, target_position)

        distance = float('inf')

        while distance > self.distanceTreshHold:
            time.sleep(0.5)

            # Получаем позицию робота
            robot_position = self.sim.getObjectPosition(self.robot_handle, self.floor_handle)

            # Получаем позицию целевой точки
            target_position = self.sim.getObjectPosition(self.target_handle, self.floor_handle)

            # Вычисляем расстояние
            diff = np.array(robot_position[:2]) - np.array(target_position[:2])
            distance = np.sqrt(diff.dot(diff))

        return point_handle

    def getCurrentPosition(self):
        robot_position = self.sim.getObjectPosition(self.robot_handle, -1)
        return [robot_position[0], robot_position[1]]

    def execute_path(self, path_points):
        """
        Выполняет путь по списку точек.

        Args:
            path_points: список кортежей (id, x, y), например:
                         [(1, 10.5, -5.2), (2, 15.3, -8.1), ...]

        Создаёт dummy с именем по id, ведёт робота по точкам,
        после завершения — удаляет все созданные dummy.
        """
        if not path_points:
            print("Путь пустой — ничего не делаем.")
            return

        created_dummies = []  # Список хэндлов созданных dummy для последующего удаления

        try:
            print(f"Начинаем выполнение пути из {len(path_points)} точек.")

            for point_id, x, y in path_points:
                # Создаём dummy
                dummy_handle = self.sim.createDummy(0.1)  # размер 0.1 м
                if dummy_handle == -1:
                    print(f"Ошибка создания dummy для точки id={point_id}")
                    continue

                # Задаём имя по id
                self.sim.setObjectAlias(dummy_handle, str(point_id))

                # Устанавливаем позицию относительно floor
                pos = [x, y, 0]  # чуть выше, чтобы было видно
                self.sim.setObjectPosition(dummy_handle, self.floor_handle, pos)

                created_dummies.append(dummy_handle)

                print(f"Создана waypoint dummy id={point_id} на ({x:.3f}, {y:.3f})")

            # Едем к этой точке (используем основной target)
            for point_handle in created_dummies:
                self.moveToPoint(point_handle)

            print("Путь полностью пройден!")

        finally:
            # УДАЛЕНИЕ всех созданных dummy (даже если ошибка)
            print("Удаляем waypoint dummy...")
            for handle in created_dummies:
                self.sim.removeObject(handle)
            print("Все waypoint'ы удалены.")

    def getPosition(self):
        return self.sim.getObjectPosition(self.robot_handle, self.floor_handle)