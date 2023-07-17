from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

class Task(BaseModel):
    name: str
    method: str
    url: str
    headers: str
    params: str
    timeout: int
    status_code: int
    interval: int
    keyword: str

# 定义数据库连接池
class DB:
    def __init__(self, db_name):
        self.db_name = db_name
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (name TEXT PRIMARY KEY,method TEXT,url TEXT,headers TEXT,
                    params TEXT,
                    timeout INTEGER,
                    status_code INTEGER,
                    interval INTEGER,
                    keyword TEXT
                )
            ''')

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

app = FastAPI()
db = DB('apimonitor.db')

@app.post("/tasks/")
async def create_task(task: Task):
    with db as cursor:
        cursor.execute('''INSERT INTO tasks(name, method, url, headers, params, timeout, status_code, interval, keyword)
                          VALUES(:name,:method,:url,:headers,:params,:timeout,:status_code,:interval,:keyword)''',
                       task.dict())
    return {**task.dict(), 'message': 'Task created'}

@app.get("/tasks/")
async def read_tasks():
    with db as cursor:
        cursor.execute('SELECT name, method, url, headers, params, timeout, status_code, interval, keyword FROM tasks')
        tasks = cursor.fetchall()
    return {'tasks': tasks}

@app.get("/tasks/{task_name}")
async def read_task(task_name: str):
    with db as cursor:
        cursor.execute('SELECT name, method, url, headers, params, timeout, status_code, interval, keyword FROM tasks WHERE name=?', (task_name,))
        task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {'task': task}

@app.put("/tasks/{task_name}")
async def update_task(task_name: str, task: Task):
    with db as cursor:
        cursor.execute('''UPDATE tasks SET method=:method, url=:url, headers=:headers, params=:params, 
                          timeout=:timeout, status_code=:status_code, interval=:interval, keyword=:keyword WHERE name=:name''',
                       task.dict())
    return {'message': 'Task updated'}

@app.delete("/tasks/{task_name}")
async def delete_task(task_name: str):
    with db as cursor:
        cursor.execute("DELETE FROM tasks WHERE name=?", (task_name,))
    return {'message': 'Task deleted'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)