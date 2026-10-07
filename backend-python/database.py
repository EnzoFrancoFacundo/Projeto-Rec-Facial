import sqlite3
import os
import pickle
from datetime import datetime

DB_PATH = "faces.db"

class FaceDatabase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_tables()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_encodings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                encoding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recognition_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                confidence REAL,
                recognized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        ''')
        
    
    def add_user(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_user_by_name(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM users ORDER BY name")
        users = cursor.fetchall()
        conn.close()
        return users
    
    def update_user_name(self, old_name, new_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?", (new_name, old_name))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def delete_user(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        user = self.get_user_by_name(name)
        if not user:
            return False
        user_id = user[0]
        cursor.execute("DELETE FROM face_encodings WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    
    def add_encoding(self, user_id, encoding):
        encoding_bytes = pickle.dumps(encoding)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO face_encodings (user_id, encoding) VALUES (?, ?)", (user_id, encoding_bytes))
        conn.commit()
        conn.close()
        return cursor.lastrowid
    
    def get_encodings_by_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT encoding FROM face_encodings WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        encodings = []
        for row in rows:
            encodings.append(pickle.loads(row[0]))
        return encodings
    
    def get_all_encodings(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.name, fe.encoding 
            FROM users u
            JOIN face_encodings fe ON u.id = fe.user_id
        ''')
        rows = cursor.fetchall()
        conn.close()
        encodings, names, ids = [], [], []
        for row in rows:
            ids.append(row[0])
            names.append(row[1])
            encodings.append(pickle.loads(row[2]))
        return encodings, names, ids
    
    def add_recognition_log(self, user_id, confidence):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO recognition_logs (user_id, confidence) VALUES (?, ?)", (user_id, confidence))
        conn.commit()
        conn.close()
    
    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM face_encodings")
        total_encodings = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM recognition_logs")
        total_logs = cursor.fetchone()[0]
        conn.close()
        return {"total_users": total_users, "total_encodings": total_encodings, "total_logs": total_logs}