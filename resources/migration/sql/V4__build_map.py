# import pygame
import random
import math
import sys
import sqlalchemy as sa
import os

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)


class PRM:
    def __init__(self, n_samples=300, safety_margin = 1):
        """
        Args:
            map_bounds: (min_x, min_y, max_x, max_y) реальные границы карты
            obstacles: препятствия в реальных координатах (x, y, width, height)
            n_samples: количество точек
            connection_radius: радиус соединения в реальных координатах
        """
        self.n_samples = n_samples
        self.nodes = []
        self.graph = {}
        self.visualization_steps = []  # Для анимации построения
        self.safety_margin = safety_margin
        self.status = 0

        username = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = os.getenv('FLYWAY_HOST')
        port = os.getenv('DB_PORT')
        database = os.getenv('DB_NAME')

        url = f'postgresql://{username}:{password}@{host}:{port}/{database}'
        self.engine = sa.create_engine(url)

        buildings = self.get_buildings()
        if buildings == -1:
            self.status = -1

        # Преобразуем в формат (x, y, width, height) в реальных координатах
        self.obstacles = [
            (
                float(b['x1']),
                float(b['y1']),
                float(b['x2']) - float(b['x1']),
                float(b['y2']) - float(b['y1'])
            )
            for b in buildings
        ]

        self.map_bounds = self.get_map_bounds(buildings, margin_ratio=0.1)

        self.min_x, self.min_y, self.max_x, self.max_y = self.map_bounds

        # Вычисляем адекватный радиус соединения (10% от диагонали карты)
        map_width = self.map_bounds[2] - self.map_bounds[0]
        map_height = self.map_bounds[3] - self.map_bounds[1]
        diagonal = math.sqrt(map_width ** 2 + map_height ** 2)
        self.connection_radius = diagonal * 0.1

        self.build_roadmap()

    def get_buildings(self):
        buildings = []

        try:
            with self.engine.connect() as conn:
                request = sa.text("""SELECT * FROM building bu JOIN body b ON b.id = bu.body_id""")
                result = conn.execute(request)
                buildings = [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error: {e}")
            return -1

        return buildings

    def build_roadmap(self):
        """Строит вероятностную дорожную карту"""
        self.nodes = []
        self.graph = {}
        self.visualization_steps = []

        # 1. Генерация случайных точек
        self.generate_free_points()

        # 2. Соединение соседних точек
        self.connect_neighbors()

        return self.graph

    def generate_free_points(self):
        """Генерирует точки в свободном пространстве (реальные координаты)"""
        attempts = 0
        max_attempts = self.n_samples * 3

        while len(self.nodes) < self.n_samples and attempts < max_attempts:
            # Генерируем в реальных границах
            point = (
                random.uniform(self.min_x, self.max_x),
                random.uniform(self.min_y, self.max_y)
            )

            if self.is_point_free(point):
                self.nodes.append(point)
                self.graph[point] = []
                # Сохраняем шаг для визуализации
                self.visualization_steps.append(('point', point))

            attempts += 1

    def connect_neighbors(self):
        """Соединяет точки в радиусе connection_radius (реальные координаты)"""
        for i, node1 in enumerate(self.nodes):
            for j, node2 in enumerate(self.nodes):
                if i < j and self.distance(node1, node2) <= self.connection_radius:
                    if self.is_collision_free(node1, node2):
                        # Добавляем в обе стороны (ненаправленный граф)
                        cost = self.distance(node1, node2)
                        self.graph[node1].append((node2, cost))
                        self.graph[node2].append((node1, cost))
                        # Сохраняем шаг для визуализации
                        self.visualization_steps.append(('edge', (node1, node2)))

    def is_point_free(self, point):
        """Проверяет минимальное евклидово расстояние до препятствий"""
        x, y = point

        for obstacle in self.obstacles:
            ox, oy, ow, oh = obstacle

            # Находим ближайшую точку на прямоугольнике к нашей точке
            closest_x = max(ox, min(x, ox + ow))
            closest_y = max(oy, min(y, oy + oh))

            # Вычисляем расстояние
            distance = math.sqrt((x - closest_x) ** 2 + (y - closest_y) ** 2)

            # Если расстояние меньше безопасной зоны
            if distance < self.safety_margin:
                return False

        return True

    def distance(self, pos1, pos2):
        """Евклидово расстояние между двумя точками (реальные координаты)"""
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

    def is_collision_free(self, pos1, pos2):
        """Проверяет, нет ли столкновений на пути между двумя точками (реальные координаты)"""
        for obstacle in self.obstacles:
            if self.line_rectangle_collision(pos1, pos2, obstacle):
                return False
        return True

    def line_rectangle_collision(self, p1, p2, rect):
        """Проверяет пересечение линии с прямоугольником (реальные координаты)"""
        x, y, w, h = rect

        # Проверяем пересечение с каждой стороной прямоугольника
        lines = [
            [(x, y), (x + w, y)],  # верх
            [(x + w, y), (x + w, y + h)],  # право
            [(x + w, y + h), (x, y + h)],  # низ
            [(x, y + h), (x, y)]  # лево
        ]

        for line in lines:
            if self.line_line_collision(p1, p2, line[0], line[1]):
                return True
        return False

    def line_line_collision(self, p1, p2, p3, p4):
        """Проверяет пересечение двух отрезков (реальные координаты)"""

        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    def find_path(self, start, end):
        """Находит путь от start до end с помощью A* (реальные координаты)"""
        if start not in self.graph or end not in self.graph:
            return None

        # Эвристика - евклидово расстояние
        def heuristic(node):
            return self.distance(node, end)

        # A* алгоритм
        open_set = {start}
        came_from = {}
        g_score = {node: float('inf') for node in self.graph}
        g_score[start] = 0
        f_score = {node: float('inf') for node in self.graph}
        f_score[start] = heuristic(start)

        while open_set:
            current = min(open_set, key=lambda node: f_score[node])

            if current == end:
                # Восстанавливаем путь
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            open_set.remove(current)

            for neighbor, cost in self.graph[current]:
                tentative_g_score = g_score[current] + cost

                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor)
                    if neighbor not in open_set:
                        open_set.add(neighbor)

        return None

    def get_map_bounds(self, buildings_data, margin_ratio=0.1):
        """
        Определяет реальные границы карты на основе зданий

        Args:
            buildings_data: Список словарей с координатами зданий
            margin_ratio: Отступ от крайних зданий (в процентах от размера)

        Returns:
            tuple: (min_x, min_y, max_x, max_y)
        """
        if not buildings_data:
            return (0, 0, 1000, 700)  # Дефолтные значения

        # Собираем все координаты
        all_x = []
        all_y = []

        for b in buildings_data:
            all_x.append(float(b['x1']))
            all_x.append(float(b['x2']))
            all_y.append(float(b['y1']))
            all_y.append(float(b['y2']))

        # Находим границы
        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)

        # Добавляем отступ
        width = max_x - min_x
        height = max_y - min_y

        margin_x = width * margin_ratio
        margin_y = height * margin_ratio

        return (
            min_x - margin_x,
            min_y - margin_y,
            max_x + margin_x,
            max_y + margin_y
        )

    def real_to_screen(self, point, map_bounds, screen_size):
        """
        Преобразует реальные координаты в экранные

        Args:
            point: (x, y) реальные координаты
            map_bounds: (min_x, min_y, max_x, max_y) границы реальной карты
            screen_size: (width, height) размер окна PyGame

        Returns:
            tuple: (screen_x, screen_y)
        """
        min_x, min_y, max_x, max_y = map_bounds
        screen_width, screen_height = screen_size

        # Линейное преобразование
        screen_x = ((point[0] - min_x) / (max_x - min_x)) * screen_width
        screen_y = ((point[1] - min_y) / (max_y - min_y)) * screen_height

        # Инвертируем Y (в PyGame Y увеличивается вниз)
        screen_y = screen_height - screen_y

        return (int(screen_x), int(screen_y))

    def screen_to_real(self, point, map_bounds, screen_size):
        """
        Преобразует экранные координаты в реальные

        Args:
            point: (x, y) экранные координаты
            map_bounds: (min_x, min_y, max_x, max_y) границы реальной карты
            screen_size: (width, height) размер окна PyGame

        Returns:
            tuple: (real_x, real_y)
        """
        min_x, min_y, max_x, max_y = map_bounds
        screen_width, screen_height = screen_size
        screen_x, screen_y = point

        # Инвертируем Y
        screen_y = screen_height - screen_y

        # Линейное преобразование
        real_x = min_x + (screen_x / screen_width) * (max_x - min_x)
        real_y = min_y + (screen_y / screen_height) * (max_y - min_y)

        return (real_x, real_y)

    def draw_roadmap(screen, prm, map_bounds, current_step=0, show_animation=True,
                     path=None, start_point=None, end_point=None):
        """Отрисовывает карту PRM с преобразованием координат"""
        # screen.fill(WHITE)
        #
        # screen_size = screen.get_size()
        #
        # # Рисуем препятствия (преобразуем в экранные координаты)
        # for obstacle in prm.obstacles:
        #     ox, oy, w, h = obstacle
        #
        #     # Получаем углы прямоугольника
        #     corners = [
        #         (ox, oy),
        #         (ox + w, oy),
        #         (ox + w, oy + h),
        #         (ox, oy + h)
        #     ]
        #
        #     # Преобразуем в экранные координаты
        #     screen_corners = [real_to_screen(p, map_bounds, screen_size) for p in corners]
        #
        #     # Рисуем заливку
        #     pygame.draw.polygon(screen, DARK_GRAY, screen_corners)
        #     # Рисуем контур
        #     pygame.draw.polygon(screen, BLACK, screen_corners, 2)
        #
        # if show_animation and current_step < len(prm.visualization_steps):
        #     # Анимированное построение
        #     for step_type, data in prm.visualization_steps[:current_step]:
        #         if step_type == 'point':
        #             screen_point = real_to_screen(data, map_bounds, screen_size)
        #             pygame.draw.circle(screen, BLUE, screen_point, 3)
        #         elif step_type == 'edge':
        #             screen_p1 = real_to_screen(data[0], map_bounds, screen_size)
        #             screen_p2 = real_to_screen(data[1], map_bounds, screen_size)
        #             pygame.draw.line(screen, GRAY, screen_p1, screen_p2, 1)
        # else:
        #     # Полная отрисовка
        #     # Сначала рёбра
        #     for node, neighbors in prm.graph.items():
        #         screen_node = real_to_screen(node, map_bounds, screen_size)
        #         for neighbor, cost in neighbors:
        #             screen_neighbor = real_to_screen(neighbor, map_bounds, screen_size)
        #             pygame.draw.line(screen, GRAY, screen_node, screen_neighbor, 2)
        #
        #     # Потом узлы
        #     for node in prm.nodes:
        #         screen_node = real_to_screen(node, map_bounds, screen_size)
        #         pygame.draw.circle(screen, BLUE, screen_node, 4)
        #         pygame.draw.circle(screen, WHITE, screen_node, 2)
        #
        # # Рисуем путь если есть
        # if path and len(path) > 1:
        #     for i in range(len(path) - 1):
        #         screen_p1 = real_to_screen(path[i], map_bounds, screen_size)
        #         screen_p2 = real_to_screen(path[i + 1], map_bounds, screen_size)
        #         pygame.draw.line(screen, GREEN, screen_p1, screen_p2, 4)
        #
        # # Рисуем стартовую и конечную точки
        # if start_point:
        #     screen_start = real_to_screen(start_point, map_bounds, screen_size)
        #     pygame.draw.circle(screen, GREEN, screen_start, 10)
        #     pygame.draw.circle(screen, WHITE, screen_start, 4)
        # if end_point:
        #     screen_end = real_to_screen(end_point, map_bounds, screen_size)
        #     pygame.draw.circle(screen, RED, screen_end, 10)
        #     pygame.draw.circle(screen, WHITE, screen_end, 4)

    def flush(self):
        saved_points = {}

        with self.engine.connect() as conn:
            print("Читим старый граф карты...")
            with conn.begin():
                conn.execute(sa.text("DELETE FROM edge"))
                conn.execute(sa.text("DELETE FROM point"))

            print("Добавляем вершины...")
            for point in self.nodes:
                with conn.begin():
                    insert_point_stmt = sa.text("""
                                                        INSERT INTO point (x, y)
                                                        VALUES (:x, :y)
                                                        RETURNING id
                                                    """)
                    x, y = point
                    result = conn.execute(insert_point_stmt, {
                        "x": x,
                        "y": y
                    })

                    point_id = result.scalar_one()
                    saved_points[point] = point_id

            print("Добавляем рёбра...")
            for point in saved_points.keys():
                id = saved_points[point]
                with conn.begin():
                    for edge in self.graph[point]:
                        coords, _ = edge
                        second_id = saved_points[coords]

                        insert_point_stmt = sa.text("""
                                                                                INSERT INTO edge (parent_id, child_id)
                                                                                VALUES (:first, :second)
                                                                            """)

                        conn.execute(insert_point_stmt, {
                            "first": id,
                            "second": second_id
                        })

        print("✅ Карта построена")

    def close(self):
        self.engine.dispose()


def main():
    # pygame.init()
    SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
    # screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    # pygame.display.set_caption("PRM Map Builder - Courier Robot Navigation")
    # clock = pygame.time.Clock()

    # Создаем PRM с реальными координатами
    prm = PRM(
        n_samples=300,
    )

    roadmap = prm.build_roadmap()

    prm.flush()
    prm.close()

    # Переменные для визуализации
    # animation_speed = 10  # шагов в кадр
    # current_step = 0
    # show_animation = True
    # animation_finished = False
    #
    # # Точки для навигации (в реальных координатах)
    # start_point = None
    # end_point = None
    # current_path = None
    #
    # # Для отладки: покажем границы
    # print(f"Number of obstacles: {len(obstacles)}")
    # print(f"Number of PRM nodes: {len(prm.nodes)}")
    #
    # running = True
    # while running:
    #     for event in pygame.event.get():
    #         if event.type == pygame.QUIT:
    #             running = False
    #         elif event.type == pygame.KEYDOWN:
    #             if event.key == pygame.K_r:
    #                 # Перестроить карту
    #                 prm = PRM(
    #                     map_bounds=map_bounds,
    #                     obstacles=obstacles,
    #                     n_samples=400,
    #                     connection_radius=connection_radius
    #                 )
    #                 roadmap = prm.build_roadmap()
    #                 current_step = 0
    #                 animation_finished = False
    #                 start_point = None
    #                 end_point = None
    #                 current_path = None
    #             elif event.key == pygame.K_SPACE:
    #                 # Пропустить анимацию/показать полную карту
    #                 show_animation = not show_animation
    #             elif event.key == pygame.K_c:
    #                 # Очистить путь
    #                 current_path = None
    #                 start_point = None
    #                 end_point = None
    #             elif event.key == pygame.K_p:
    #                 # Случайные точки для пути (в реальных координатах)
    #                 if prm.nodes:
    #                     start_point = random.choice(prm.nodes)
    #                     end_point = random.choice(prm.nodes)
    #                     while end_point == start_point:
    #                         end_point = random.choice(prm.nodes)
    #                     current_path = prm.find_path(start_point, end_point)
    #                     if current_path:
    #                         print(f"Path found with {len(current_path)} points")
    #                     else:
    #                         print("No path found")
    #             elif event.key == pygame.K_d:
    #                 # Отладочная информация
    #                 print(f"Map bounds: {map_bounds}")
    #                 print(f"Screen size: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    #                 print(f"Start: {start_point}, End: {end_point}")
    #                 print(f"Path length: {len(current_path) if current_path else 0}")
    #
    #         elif event.type == pygame.MOUSEBUTTONDOWN:
    #             # Преобразуем экранные координаты в реальные
    #             screen_point = event.pos
    #             real_point = screen_to_real(screen_point, map_bounds, (SCREEN_WIDTH, SCREEN_HEIGHT))
    #
    #             if event.button == 1:  # Левая кнопка - старт
    #                 start_point = real_point
    #                 print(f"Start point set: {real_point}")
    #                 if end_point:
    #                     current_path = prm.find_path(start_point, end_point)
    #                     if current_path:
    #                         print(f"Path found with {len(current_path)} points")
    #                     else:
    #                         print("No path found")
    #             elif event.button == 3:  # Правая кнопка - финиш
    #                 end_point = real_point
    #                 print(f"End point set: {real_point}")
    #                 if start_point:
    #                     current_path = prm.find_path(start_point, end_point)
    #                     if current_path:
    #                         print(f"Path found with {len(current_path)} points")
    #                     else:
    #                         print("No path found")
    #
    #     # Обновление анимации
    #     if show_animation and not animation_finished:
    #         current_step += animation_speed
    #         if current_step >= len(prm.visualization_steps):
    #             current_step = len(prm.visualization_steps)
    #             animation_finished = True
    #
    #     # Отрисовка
    #     draw_roadmap(screen, prm, map_bounds, current_step, show_animation,
    #                  current_path, start_point, end_point)
    #
    #     pygame.display.flip()
    #     clock.tick(60)
    #
    # pygame.quit()
    # sys.exit()


if __name__ == "__main__":
    main()