import random
import math
import sys
import sqlalchemy as sa
import os
import pygame

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
ORANGE = (255, 165, 0)
LIGHT_BLUE = (173, 216, 230)


class PRM:
    def __init__(self, n_samples=300, safety_margin=1):
        self.n_samples = n_samples
        self.nodes = []
        self.graph = {}
        self.visualization_steps = []
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
        roads = self.get_roads()
        pedestrian_crossings = self.get_pedestrian_crossings()
        if buildings == -1 or roads == -1 or pedestrian_crossings == -1:
            self.status = -1
            return

        # Препятствия (здания)
        self.obstacles = []
        for b in buildings:
            x1, y1, x2, y2 = float(b['x1']), float(b['y1']), float(b['x2']), float(b['y2'])
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            self.obstacles.append((min_x, min_y, max_x - min_x, max_y - min_y))

        # Дороги (отдельно, чтобы рисовать другим цветом)
        self.road_rects = []
        for r in roads:
            x1, y1, x2, y2 = float(r['x1']), float(r['y1']), float(r['x2']), float(r['y2'])
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            rect = (min_x, min_y, max_x - min_x, max_y - min_y)
            self.road_rects.append(rect)
            self.obstacles.append(rect)  # дороги тоже препятствия для поиска пути

        # Мосты (пешеходные переходы)
        self.bridges = []
        for pc in pedestrian_crossings:
            x1, y1, x2, y2 = float(pc['x1']), float(pc['y1']), float(pc['x2']), float(pc['y2'])
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            self.bridges.append((min_x, min_y, max_x - min_x, max_y - min_y))

        self.map_bounds = self.get_map_bounds(buildings, margin_ratio=0.1)
        self.min_x, self.min_y, self.max_x, self.max_y = self.map_bounds

        map_width = self.max_x - self.min_x
        map_height = self.max_y - self.min_y
        diagonal = math.sqrt(map_width ** 2 + map_height ** 2)
        self.connection_radius = diagonal * 0.1

        self.build_roadmap()

    def __del__(self):
        self.close()

    def get_buildings(self):
        try:
            with self.engine.connect() as conn:
                request = sa.text("SELECT * FROM building bu JOIN body b ON b.id = bu.body_id")
                result = conn.execute(request)
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error loading buildings: {e}")
            return -1

    def get_roads(self):
        try:
            with self.engine.connect() as conn:
                request = sa.text("SELECT * FROM road r JOIN body b ON b.id = r.body_id")
                result = conn.execute(request)
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error loading roads: {e}")
            return -1

    def get_pedestrian_crossings(self):
        try:
            with self.engine.connect() as conn:
                request = sa.text("SELECT * FROM pedestrian_crossing pc JOIN body b ON b.id = pc.body_id")
                result = conn.execute(request)
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error loading pedestrian crossings: {e}")
            return -1

    def build_roadmap(self):
        self.nodes = []
        self.graph = {}
        self.visualization_steps = []
        self.add_bridge_edges()
        self.generate_free_points()
        self.connect_neighbors()
        return self.graph

    def generate_free_points(self):
        attempts = 0
        max_attempts = self.n_samples * 3
        while len(self.nodes) < self.n_samples and attempts < max_attempts:
            point = (
                random.uniform(self.min_x, self.max_x),
                random.uniform(self.min_y, self.max_y)
            )
            if self.is_point_free(point):
                self.nodes.append(point)
                self.graph[point] = []
                self.visualization_steps.append(('point', point))
            attempts += 1

    def connect_neighbors(self):
        for i, node1 in enumerate(self.nodes):
            for j, node2 in enumerate(self.nodes):
                if i < j and self.distance(node1, node2) <= self.connection_radius:
                    if self.is_collision_free(node1, node2):
                        cost = self.distance(node1, node2)
                        self.graph[node1].append((node2, cost, 'default'))
                        self.graph[node2].append((node1, cost, 'default'))
                        self.visualization_steps.append(('edge', (node1, node2)))

    def add_bridge_edges(self):
        for bridge in self.bridges:
            ox, oy, ow, oh = bridge
            left_x, right_x = ox, ox + ow
            bottom_y, top_y = oy, oy + oh
            if ow < oh:
                first_p = (ox + ow / 2, bottom_y)
                second_p = (ox + ow / 2, top_y)
            else:
                first_p = (left_x, oy + oh / 2)
                second_p = (right_x, oy + oh / 2)
            self.nodes.append(first_p)
            self.graph[first_p] = []
            self.visualization_steps.append(('point', first_p))
            self.nodes.append(second_p)
            self.graph[second_p] = []
            self.visualization_steps.append(('point', second_p))
            cost = self.distance(first_p, second_p)
            self.graph[first_p].append((second_p, cost, 'pedestrian_crossings'))
            self.graph[second_p].append((first_p, cost, 'pedestrian_crossings'))
            self.visualization_steps.append(('edge', (first_p, second_p)))

    def is_point_free(self, point):
        x, y = point
        for (ox, oy, ow, oh) in self.obstacles:
            closest_x = max(ox, min(x, ox + ow))
            closest_y = max(oy, min(y, oy + oh))
            dist = math.sqrt((x - closest_x) ** 2 + (y - closest_y) ** 2)
            if dist < self.safety_margin:
                return False
        return True

    def is_collision_free(self, pos1, pos2):
        for obs in self.obstacles:
            if self.line_rectangle_collision(pos1, pos2, obs):
                return False
        return True

    def line_rectangle_collision(self, p1, p2, rect):
        x, y, w, h = rect
        lines = [
            [(x, y), (x + w, y)],
            [(x + w, y), (x + w, y + h)],
            [(x + w, y + h), (x, y + h)],
            [(x, y + h), (x, y)]
        ]
        for line in lines:
            if self.line_line_collision(p1, p2, line[0], line[1]):
                return True
        return False

    def line_line_collision(self, p1, p2, p3, p4):
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    def distance(self, pos1, pos2):
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

    def get_map_bounds(self, buildings_data, margin_ratio=0.1):
        all_x, all_y = [], []
        for b in buildings_data:
            all_x.extend([float(b['x1']), float(b['x2'])])
            all_y.extend([float(b['y1']), float(b['y2'])])

        if hasattr(self, 'obstacles'):
            for obs in self.obstacles:
                all_x.append(obs[0])
                all_x.append(obs[0] + obs[2])
                all_y.append(obs[1])
                all_y.append(obs[1] + obs[3])
        if hasattr(self, 'bridges'):
            for br in self.bridges:
                all_x.append(br[0])
                all_x.append(br[0] + br[2])
                all_y.append(br[1])
                all_y.append(br[1] + br[3])

        if not all_x:
            return (0, 0, 1000, 700)

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        return (min_x + 15, min_y, max_x - 5, max_y)

    def flush(self):
        saved_points = {}
        with self.engine.connect() as conn:
            print("Чистим старый граф карты...")
            with conn.begin():
                conn.execute(sa.text("DELETE FROM edge"))
                conn.execute(sa.text("DELETE FROM point"))
            print("Добавляем вершины...")
            for point in self.nodes:
                with conn.begin():
                    result = conn.execute(
                        sa.text("INSERT INTO point (x, y) VALUES (:x, :y) RETURNING id"),
                        {"x": point[0], "y": point[1]}
                    )
                    point_id = result.scalar_one()
                    saved_points[point] = point_id
            print("Добавляем рёбра...")
            for point, point_id in saved_points.items():
                for neighbor, cost, edge_type in self.graph[point]:
                    nb_id = saved_points[neighbor]
                    with conn.begin():
                        conn.execute(
                            sa.text("INSERT INTO edge (parent_id, child_id, edge_type) VALUES (:p, :c, :t)"),
                            {"p": point_id, "c": nb_id, "t": edge_type}
                        )
        print("✅ Карта построена")

    def close(self):
        self.engine.dispose()

    def save_image(self, filename="map.png", image_size=(2400, 1600)):
        """Сохраняет карту как PNG-изображение (без GUI)."""
        pygame.init()
        surface = pygame.Surface(image_size)
        surface.fill(WHITE)

        def world_to_pixel(point):
            rx = (point[0] - self.min_x) / (self.max_x - self.min_x) * image_size[0]
            ry = image_size[1] - (point[1] - self.min_y) / (self.max_y - self.min_y) * image_size[1]
            return (int(rx), int(ry))

        # Здания
        for ox, oy, ow, oh in self.obstacles:
            # Пропускаем дороги, чтобы не перерисовывать
            if (ox, oy, ow, oh) in self.road_rects:
                continue
            top_left = world_to_pixel((ox, oy + oh))
            bottom_right = world_to_pixel((ox + ow, oy))
            rect = pygame.Rect(top_left, (bottom_right[0] - top_left[0], bottom_right[1] - top_left[1]))
            pygame.draw.rect(surface, DARK_GRAY, rect)
            pygame.draw.rect(surface, BLACK, rect, 2)

        # Дороги (чёрный)
        for ox, oy, ow, oh in self.road_rects:
            top_left = world_to_pixel((ox, oy + oh))
            bottom_right = world_to_pixel((ox + ow, oy))
            rect = pygame.Rect(top_left, (bottom_right[0] - top_left[0], bottom_right[1] - top_left[1]))
            pygame.draw.rect(surface, BLACK, rect)
            pygame.draw.rect(surface, DARK_GRAY, rect, 2)  # рамка чуть светлее

        # Мосты (пешеходные переходы)
        for bx, by, bw, bh in self.bridges:
            top_left = world_to_pixel((bx, by + bh))
            bottom_right = world_to_pixel((bx + bw, by))
            rect = pygame.Rect(top_left, (bottom_right[0] - top_left[0], bottom_right[1] - top_left[1]))
            pygame.draw.rect(surface, LIGHT_BLUE, rect)
            pygame.draw.rect(surface, BLUE, rect, 2)

        # Рёбра
        for node1, edges in self.graph.items():
            for node2, cost, etype in edges:
                p1 = world_to_pixel(node1)
                p2 = world_to_pixel(node2)
                color = GREEN if etype == 'default' else ORANGE
                pygame.draw.line(surface, color, p1, p2, 1)

        # Вершины
        for node in self.nodes:
            pos = world_to_pixel(node)
            pygame.draw.circle(surface, RED, pos, 4)

        pygame.image.save(surface, filename)
        print(f"✅ Карта сохранена как {filename}")
        pygame.quit()


def main():
    print("Строим PRM карту из базы данных...")
    prm = PRM(n_samples=300)

    if prm.status == -1:
        print("Ошибка подключения к БД")
        return

    print(f"Построено узлов: {len(prm.nodes)}")
    print(f"Рёбер: {sum(len(neighbors) for neighbors in prm.graph.values()) // 2}")

    prm.flush()
    prm.save_image("/flyway/output/map.bmp")
    sys.exit()


if __name__ == "__main__":
    main()