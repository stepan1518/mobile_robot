import numpy as np
import matplotlib.pyplot as plt
import os

from db import DBAbstractFactory
from kafka import KafkaConsumerFactory, KafkaConsumerService
from map import Map
from robot import ZMQRobotAbstractFactory


edges = []

consumer = KafkaConsumerFactory.create_realtime_consumer(
    bootstrap_servers=os.getenv('KAFKA_HOST', 'localhost:9094'),
    group_id=os.getenv('KAFKA_CONSUMER_GROUP', 'robot-server-group')
)

service = KafkaConsumerService(
    consumer=consumer,
    topics=[os.getenv('KAFKA_TOPIC', 'camera_events_test')]
)

service.start()

factory = ZMQRobotAbstractFactory()
robot = factory.createRobot(service)

db_connection = DBAbstractFactory.createDBConnection()
city_map = Map(db_connection)
robot_pos = robot.getPosition()
city_map.vertices[-1] = (robot_pos[0], robot_pos[1])

city_map.graph[-1] = {}
for point_id in city_map.vertices.keys():
    x, y = city_map.vertices[point_id]
    diff = np.array([x, y]) - np.array(robot_pos[:2])
    distance = np.sqrt(diff.dot(diff))

    if distance <= 5:
        city_map.edges.append((x, y, robot_pos[0], robot_pos[1], point_id, -1, 'default'))
        city_map.edges.append((robot_pos[0], robot_pos[1], x, y, -1, point_id, 'default'))

        city_map.graph[point_id][-1] = (distance, 'default')
        city_map.graph[-1][point_id] = (distance, 'default')

ids = city_map.vertices.keys()
path = city_map.findShortestPath(-1, 3407)

plt.scatter([v[1][0] for v in city_map.vertices.items()], [v[1][1] for v in city_map.vertices.items()])
for v_name in city_map.vertices.keys():
    x, y = city_map.vertices[v_name]
    plt.annotate(v_name, xy=(x, y), textcoords="offset points", xytext=(5, 5), ha='center')
for edje in city_map.edges:
    x1, y1, x2, y2, p1_name, p2_name, _ = edje

    if x2 and y2:
        plt.plot([float(x1), float(x2)], [float(y1), float(y2)], color='blue')

print(path)
if path != None:
    current, _ = path[0]
    for v_name, _ in path:
        x1, y1 = city_map.vertices[current]
        x2, y2 = city_map.vertices[v_name]
        plt.plot([float(x1), float(x2)], [float(y1), float(y2)], color='red', linewidth=5)

        current = v_name

#Настройка графика
plt.title('Карта')
plt.xlabel('X')
plt.ylabel('Y')
plt.grid(True)
plt.show()

plt.show()

path_to_execute = []
for id, edge_type in path:
    x, y = city_map.vertices[id]
    path_to_execute.append((id, x, y, edge_type))

robot.execute_path(path_to_execute)

service.stop()
print('Робот прибыл')