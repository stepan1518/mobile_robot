from db import DBAbstractFactory
from map import Map
from robot import ZMQRobotAbstractFactory
import matplotlib.pyplot as plt


edges = []

factory = ZMQRobotAbstractFactory()
robot = factory.createRobot()

db_connection = DBAbstractFactory.createDBConnection()
city_map = Map(db_connection)
path = city_map.findShortestPath(955, 1076)

plt.scatter([v[1][0] for v in city_map.vertices.items()], [v[1][1] for v in city_map.vertices.items()])
for v_name in city_map.vertices.keys():
    x, y = city_map.vertices[v_name]
    plt.annotate(v_name, xy=(x, y), textcoords="offset points", xytext=(5, 5), ha='center')
for edje in city_map.edges:
    x1, y1, x2, y2, p1_name, p2_name = edje

    if x2 and y2:
        plt.plot([float(x1), float(x2)], [float(y1), float(y2)], color='blue')

print(path)
if path != None:
    current = path[0]
    for v_name in path:
        x1, y1 = city_map.vertices[current]
        x2, y2 = city_map.vertices[v_name]
        plt.plot([float(x1), float(x2)], [float(y1), float(y2)], color='red', linewidth=5)

        current = v_name

# # Настройка графика
plt.title('Карта')
plt.xlabel('X')
plt.ylabel('Y')
plt.grid(True)
plt.show()

plt.show()

path_to_execute = []
for id in path:
    x, y = city_map.vertices[id]
    path_to_execute.append((id, x, y))

robot.execute_path(path_to_execute)
# for nextDummy in path:
#     robot.moveToPoint(city_map.vertices[nextDummy])

print('Робот прибыл')