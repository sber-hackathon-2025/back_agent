import sqlite3


class DbAdapter:
    def __init__(self):
        self.functions_db = sqlite3.connect("../db/functions.db")

    def init_db(self):
        cursor = self.functions_db.cursor()
        # Создаем таблицу, если ее нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vector TEXT NOT NULL,  
                url TEXT,              
                code TEXT              
            )
        """)
        self.functions_db.commit()

    def get_by_vectors(self, vectors: list[str]) -> list[str]:
        # Получение кодов из SQLite
        cursor = self.functions_db.cursor()
        cursor.execute(
            "SELECT code, url FROM functions WHERE vector IN (%s)"
            % ",".join("?" * len(vectors)),
            vectors,
        )
        return cursor.fetchall()

    def add_entity(self, vector: str, code: str, url: str):
        if not isinstance(vector, str):
            vector = str(vector)
        # Добавляем в SQLite
        cursor = self.functions_db.cursor()
        cursor.execute(
            "INSERT INTO functions (vector, code, url) VALUES (?, ?, ?)",
            (vector, code, url),
        )
        self.functions_db.commit()

    def close_db(self):
        self.functions_db.close()
