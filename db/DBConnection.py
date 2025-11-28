import os
import sqlalchemy as sa

class DBConnection:

    engine = None

    def __init__(self):
        username = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = os.getenv('DB_HOST')
        port = os.getenv('DB_PORT')
        database = os.getenv('DB_NAME')

        url = f'postgresql://{username}:{password}@{host}:{port}/{database}'

        # Создаем движок подключения
        self.engine = sa.create_engine(url)
        print('Соединение с базой установлено')

    def execute(self, query):

        result = None

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sa.text(query))
        finally:
            pass

        return result

    def __del__(self):
        self.close()

    def close(self):
        self.engine.dispose()