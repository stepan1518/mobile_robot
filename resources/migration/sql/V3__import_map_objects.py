import os
import sys
import sqlalchemy as sa

sys.path.insert(0, '/coppeliaSim/zmqRemoteApi/clients/python/src')

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

ZMQ_HOST = os.getenv('FLYWAY_HOST')

def parse_buildings():
    print("Подключаемся к CoppeliaSim...")
    client = RemoteAPIClient(host=ZMQ_HOST)
    sim = client.getObject('sim')
    print("ПОДКЛЮЧЕНО!")

    building_handles = []

    # Получаем все объекты в сцене
    all_objects = sim.getObjectsInTree(sim.handle_scene)

    for handle in all_objects:
        # Получаем всех прямых детей этого объекта
        children = []
        child_index = 0
        while True:
            child = sim.getObjectChild(handle, child_index)
            if child == -1:
                break
            children.append(child)
            child_index += 1

        # Если не ровно 3 ребёнка — пропускаем
        if len(children) != 3:
            continue

        # Получаем алиасы всех трёх детей
        child_aliases = [sim.getObjectAlias(child) for child in children]

        # Сортируем, чтобы порядок не имел значения
        child_aliases.sort()

        # Проверяем точное совпадение с нужными тремя именами
        required = ["body", "windowElement", "windows"]
        required.sort()  # на всякий случай

        if child_aliases == required:
            building_handles.append(handle)
            name = sim.getObjectAlias(handle)  # оставляем для вывода и JSON
            print(f"Найдено здание: {name} (по структуре: body, windowElement, windows)")

    print(f"\nВсего найдено зданий по структуре: {len(building_handles)}")

    map_buildings = []
    for building_handle in building_handles:
        name = sim.getObjectAlias(building_handle)

        # Находим body внутри
        children = sim.getObjectsInTree(building_handle)
        body_handle = next((c for c in children if sim.getObjectAlias(c) == "body"), None)

        if not body_handle:
            continue

        # Позиция body в мировых координатах
        floor_handle = sim.getObject(f'./floor')
        pos = sim.getObjectPosition(body_handle, floor_handle)
        cx, cy, cz = pos

        # Локальный BB body
        min_x = sim.getObjectFloatParam(body_handle, sim.objfloatparam_modelbbox_min_x)
        min_y = sim.getObjectFloatParam(body_handle, sim.objfloatparam_modelbbox_min_y)
        max_x = sim.getObjectFloatParam(body_handle, sim.objfloatparam_modelbbox_max_x)
        max_y = sim.getObjectFloatParam(body_handle, sim.objfloatparam_modelbbox_max_y)

        # Мировые координаты AABB
        world_min_x = cx + min_x
        world_min_y = cy + min_y
        world_max_x = cx + max_x
        world_max_y = cy + max_y

        map_buildings.append({
            "building": name,
            "x1": round(world_min_x, 3),
            "y1": round(world_min_y, 3),
            "x2": round(world_max_x, 3),
            "y2": round(world_max_y, 3)
        })
        print(f"{name}: ({world_min_x:.1f}, {world_min_y:.1f})")

    return map_buildings

def main() -> int:
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    host = os.getenv('FLYWAY_HOST')
    port = os.getenv('DB_PORT')
    database = os.getenv('DB_NAME')

    url = f'postgresql://{username}:{password}@{host}:{port}/{database}'

    engine = sa.create_engine(url)

    buildings = parse_buildings()

    try:
        with engine.connect() as conn:
            with conn.begin():
                print("Чистим таблицы объектов...")
                conn.execute(sa.text("DELETE FROM building"))
                conn.execute(sa.text("DELETE FROM body"))

            for b in buildings:
                with conn.begin():
                    insert_body_stmt = sa.text("""
                                    INSERT INTO body (x1, y1, x2, y2)
                                    VALUES (:x1, :y1, :x2, :y2)
                                    RETURNING id
                                """)
                    result = conn.execute(insert_body_stmt, {
                        "x1": b["x1"],
                        "y1": b["y1"],
                        "x2": b["x2"],
                        "y2": b["y2"]
                    })
                    body_id = result.scalar_one()

                    insert_building_stmt = sa.text("""
                                    INSERT INTO building (name, body_id)
                                    VALUES (:name, :body_id)
                                """)
                    conn.execute(insert_building_stmt, {
                        "name": b["building"],
                        "body_id": body_id
                    })

            print("✅ Объекты успешно импортированы")
    except Exception as e:
        print(f"Error: {e}")
        return -1
    finally:
        engine.dispose()

    return 0

if __name__ == "__main__":
    main()