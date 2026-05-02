import os
import sys
import sqlalchemy as sa
import math

sys.path.insert(0, '/coppeliaSim/zmqRemoteApi/clients/python/src')

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

ZMQ_HOST = os.getenv('FLYWAY_HOST')


def parse_roads_and_crossings():
    print("Подключаемся к CoppeliaSim...")
    client = RemoteAPIClient(host=ZMQ_HOST)
    sim = client.getObject('sim')
    print("ПОДКЛЮЧЕНО!")

    roads = []
    crossings = []

    # Получаем все объекты в сцене
    all_objects = sim.getObjectsInTree(sim.handle_scene)

    for handle in all_objects:
        alias = sim.getObjectAlias(handle)

        if 'road' in alias.lower() or 'pedestrian_crossing' in alias.lower():
            floor_handle = sim.getObject('./floor')

            # Получаем позицию объекта в мировых координатах
            pos = sim.getObjectPosition(handle, floor_handle)
            cx, cy, cz = pos

            # Получаем ориентацию относительно пола (или мира)
            orientation = sim.getObjectOrientation(handle, floor_handle)
            # ориентация: [alpha, beta, gamma] -> вращение вокруг X, Y, Z
            # В большинстве случаев поворот в плоскости XY определяется углом gamma (Z)
            gamma = orientation[2]  # радианы

            # Локальный bounding box
            min_x = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_min_x)
            min_y = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_min_y)
            max_x = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_max_x)
            max_y = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_max_y)

            # Если объект повёрнут примерно на 90° (вертикальный), меняем оси местами
            # Проверяем: abs(gamma) близок к pi/2 или 3pi/2
            if abs(abs(gamma) - math.pi / 2) < 0.1 or abs(abs(gamma) - 3 * math.pi / 2) < 0.1:
                # Меняем width и height: это эквивалентно повороту на 90°
                # Новый min/max = старый min_y, max_y для X, и старый min_x, max_x для Y
                new_min_x = min_y
                new_max_x = max_y
                new_min_y = min_x
                new_max_y = max_x
                min_x, max_x, min_y, max_y = new_min_x, new_max_x, new_min_y, new_max_y

            # Мировые координаты AABB
            world_min_x = cx + min_x
            world_min_y = cy + min_y
            world_max_x = cx + max_x
            world_max_y = cy + max_y

            item = {
                "name": alias,
                "x1": round(world_min_x, 3),
                "y1": round(world_min_y, 3),
                "x2": round(world_max_x, 3),
                "y2": round(world_max_y, 3)
            }

            if 'road' in alias.lower():
                roads.append(item)
                print(f"Найдена дорога: {alias} (gamma={math.degrees(gamma):.1f}°)")
            else:
                crossings.append(item)
                print(f"Найден пешеходный переход: {alias} (gamma={math.degrees(gamma):.1f}°)")

        # Проверяем пешеходный переход по имени
        elif 'pedestrian_crossing' in alias.lower():
            # Позиция body в мировых координатах
            floor_handle = sim.getObject('./floor')
            pos = sim.getObjectPosition(handle, floor_handle)
            cx, cy, cz = pos

            # Локальный BB body
            min_x = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_min_x)
            min_y = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_min_y)
            max_x = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_max_x)
            max_y = sim.getObjectFloatParam(handle, sim.objfloatparam_modelbbox_max_y)

            # Мировые координаты AABB
            world_min_x = cx + min_x
            world_min_y = cy + min_y
            world_max_x = cx + max_x
            world_max_y = cy + max_y

            crossings.append({
                "name": alias,
                "x1": round(world_min_x, 3),
                "y1": round(world_min_y, 3),
                "x2": round(world_max_x, 3),
                "y2": round(world_max_y, 3)
            })
            print(f"Найден пешеходный переход: {alias} ({world_min_x:.1f}, {world_min_y:.1f})")

    print(f"\nВсего найдено дорог: {len(roads)}")
    print(f"Всего найдено пешеходных переходов: {len(crossings)}")

    return roads, crossings


def main() -> int:
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    host = os.getenv('FLYWAY_HOST')
    port = os.getenv('DB_PORT')
    database = os.getenv('DB_NAME')

    url = f'postgresql://{username}:{password}@{host}:{port}/{database}'

    engine = sa.create_engine(url)

    roads, crossings = parse_roads_and_crossings()

    try:
        with engine.connect() as conn:
            with conn.begin():
                print("Чистим таблицы дорог и переходов...")
                conn.execute(sa.text("DELETE FROM road"))
                conn.execute(sa.text("DELETE FROM pedestrian_crossing"))
                conn.execute(sa.text(
                    "DELETE FROM body WHERE id IN (SELECT body_id FROM road) OR id IN (SELECT body_id FROM pedestrian_crossing)"))

            # Импорт дорог
            for road in roads:
                with conn.begin():
                    insert_body_stmt = sa.text("""
                                    INSERT INTO body (x1, y1, x2, y2)
                                    VALUES (:x1, :y1, :x2, :y2)
                                    RETURNING id
                                """)
                    result = conn.execute(insert_body_stmt, {
                        "x1": road["x1"],
                        "y1": road["y1"],
                        "x2": road["x2"],
                        "y2": road["y2"]
                    })
                    body_id = result.scalar_one()

                    insert_road_stmt = sa.text("""
                                    INSERT INTO road (name, body_id)
                                    VALUES (:name, :body_id)
                                """)
                    conn.execute(insert_road_stmt, {
                        "name": road["name"],
                        "body_id": body_id
                    })

            # Импорт пешеходных переходов
            for crossing in crossings:
                with conn.begin():
                    insert_body_stmt = sa.text("""
                                    INSERT INTO body (x1, y1, x2, y2)
                                    VALUES (:x1, :y1, :x2, :y2)
                                    RETURNING id
                                """)
                    result = conn.execute(insert_body_stmt, {
                        "x1": crossing["x1"],
                        "y1": crossing["y1"],
                        "x2": crossing["x2"],
                        "y2": crossing["y2"]
                    })
                    body_id = result.scalar_one()

                    insert_crossing_stmt = sa.text("""
                                    INSERT INTO pedestrian_crossing (name, body_id)
                                    VALUES (:name, :body_id)
                                """)
                    conn.execute(insert_crossing_stmt, {
                        "name": crossing["name"],
                        "body_id": body_id
                    })

            print("✅ Дороги и пешеходные переходы успешно импортированы")
    except Exception as e:
        print(f"Error: {e}")
        return -1
    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    main()