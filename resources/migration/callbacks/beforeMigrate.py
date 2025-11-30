#!/usr/bin/env python3
import os

print("Запускаю подготовку данных перед миграциями...")

# или просто логируем
print(f"Работаем с БД: {os.getenv('FLYWAY_URL')}")