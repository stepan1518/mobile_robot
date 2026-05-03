import heapq

class Map:

    dbConnection = None
    edges = None
    graph = None
    vertices = None

    def __init__(self, db_connection):
        self.dbConnection = db_connection
        result = self.dbConnection.execute("SELECT p.x, p.y, p2.x, p2.y, p.id, p2.id, e.edge_type FROM point p "
                                    "LEFT JOIN edge e ON p.id = e.parent_id "
                                    "LEFT JOIN point p2 ON p2.id = e.child_id")

        self.edges = []
        for row in result:
            self.edges.append(row)

        # Создаем граф в виде словаря смежности
        self.graph = {}

        for edge in self.edges:
            x1, y1, x2, y2, id1, id2, edge_type = edge

            # Рассчитываем расстояние между точками
            if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
                distance = ((float(x2) - float(x1)) ** 2 + (float(y2) - float(y1)) ** 2) ** 0.5

                # Добавляем ребро в обе стороны (ненаправленный граф)
                if id1 not in self.graph:
                    self.graph[id1] = {}
                if id2 not in self.graph:
                    self.graph[id2] = {}

                self.graph[id1][id2] = (distance, edge_type)
                self.graph[id2][id1] = (distance, edge_type)

        self.vertices = {}
        for edje in self.edges:
            x1, y1, x2, y2, id1, id2, _ = edje

            self.vertices[id1] = (float(x1), float(y1))
            if x2 and y2:
                self.vertices[id2] = (float(x2), float(y2))

    def findShortestPath(self, start_id, end_id):
        """
            Находит кратчайший путь между двумя точками с помощью алгоритма Дейкстры.

            Args:
                edges: список ребер в формате [x1, y1, x2, y2, name1, name2]
                start_id: название начальной точки
                end_id: название конечной точки

            Returns:
                list: массив названий точек, составляющих кратчайший путь
                      или None, если путь не найден
            """
        # Проверяем, что начальная и конечная точки существуют в графе
        if start_id not in self.graph or end_id not in self.graph:
            return None

        # Инициализация
        distances = {node: float('infinity') for node in self.graph}
        distances[start_id] = 0
        previous_nodes = {node: None for node in self.graph}

        # Приоритетная очередь (бинарная куча)
        priority_queue = [(0, start_id)]

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            # Если достигли конечной точки, строим путь
            if current_node == end_id:
                path = []
                while current_node is not None:
                    edge_type = 'default'
                    prev_node = None
                    node_params = previous_nodes[current_node]
                    if node_params:
                        prev_node, edge_type = previous_nodes[current_node]
                    else:
                        prev_node = None

                    path.append((current_node, edge_type))
                    current_node = prev_node
                return path[::-1]  # Разворачиваем путь

            # Если текущее расстояние больше известного, пропускаем
            if current_distance > distances[current_node]:
                continue

            # Обходим соседей
            for neighbor, edge_params in self.graph[current_node].items():
                weight, edge_type = edge_params
                distance = current_distance + weight

                # Если нашли более короткий путь
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous_nodes[neighbor] = (current_node, edge_type)
                    heapq.heappush(priority_queue, (distance, neighbor))

        # Если путь не найден
        return None