# 引入相关库
import asyncio
import aiohttp
import sqlite3
import logging
import json
from datetime import datetime
from dingtalkchatbot.chatbot import DingtalkChatbot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 设置日志格式
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

#数据库sqlite文件
DATAFILE_PATH = 'apimonitor.db'
# 初始化钉钉机器人
ding_bot = DingtalkChatbot(
    'https://oapi.dingtalk.com/robot/send?access_token=xxxx')

def send_dingbot(msg):
    """构造告警信息
    title = '通知'
    msg = f"接口 {name} 监控告警. HTTP状态码正常值 {status_code} 关键字 {keyword} 实际响应 {response.status} 实际响应 {text}"""
    # 发送告警信息
    title = '通知'
    text = msg.replace('\\n', '\n')
    text = f'# {title}\n\n{text}'
    ding_bot.send_markdown(title=title, text=text)

def get_current_time():
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_time

# 定义异步监控函数
async def monitor(session, task):
    # 解构任务
    name, method, url, headers, params, timeout, status_code, interval, keyword = task
    try:
        # 输出任务信息
        logging.info(f"执行任务: {name}, URL: {url}, headers: {headers}, params: {params}")
        # 根据请求方法执行请求
        if method.lower() == 'get':
            response = await session.get(url, headers=json.loads(headers), params=json.loads(params), timeout=timeout)
        else:
            response = await session.post(url, headers=json.loads(headers), data=json.loads(params), timeout=timeout)
        text = await response.text()
        # print(f"接口 {name} 监控告警. HTTP状态码正常值 {status_code}  实际响应 {text}")
        # 判断响应状态和关键词
        if response.status != status_code or keyword not in text:
            # 构造告警信息
            now_time = get_current_time()
            msg = f"警告-响应错误\n\n时间： {now_time}\n\n监控: {name}\n\n正常值：{status_code}-{keyword}\n\n响应状态码：{response.status}\n\n响应信息: {text}\n\n"
            send_dingbot(msg)
            logging.error(f"警告-响应错误\n\n时间： {now_time}\n\n监控: {name}\n\n正常值：{status_code}-{keyword}\n\n响应状态码：{response.status}\n\n响应信息: {text}\n\n")
    except Exception as e:
        # 发送异常信息
        # print(f"接口监控: {name} 链接错误: {str(e)}")
        now_time = get_current_time()
        msg = f"警告-响应错误\n\n时间： {now_time}\n\n监控: {name}\n\n正常值：{status_code}-{keyword}\n\n响应信息: {str(e)}\n\n"
        send_dingbot(msg)
        logging.error(msg)

# 从数据库中获取任务
def get_tasks_from_database():
    try:
        # 连接到 SQLite 数据库
        conn = sqlite3.connect(DATAFILE_PATH)
        cursor = conn.cursor()

        # 判断 tasks 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
        if cursor.fetchone() is None:
            raise sqlite3.OperationalError("数据库中'tasks'表不存在,或者未添加任务监控程序不执行")

        # 从 tasks 表获取任务数据
        cursor.execute(
            'SELECT name, method, url, headers, params, timeout, status_code, interval, keyword FROM tasks'
        )
        tasks = cursor.fetchall()
        cursor.close()
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"数据库操作错误: {str(e)}")
        return []  # 返回空列表, 因为无法获取任务

    return tasks  # 正常返回任务列表

async def update_tasks(session, scheduler):
    # 获取新的任务列表
    new_tasks = get_tasks_from_database(DATAFILE_PATH)
    # 获取当前的任务列表
    current_jobs = scheduler.get_jobs()
    current_job_ids = [job.id for job in current_jobs]
    new_task_names = [task[0] for task in new_tasks]
    # 删除不再存在的任务
    for job_id in current_job_ids:
        if job_id not in new_task_names:
            scheduler.remove_job(job_id)
    # 添加新的任务
    for task in new_tasks:
        name, _, _, _, _, _, _, interval, _ = task
        if name not in current_job_ids:
            scheduler.add_job(monitor, 'interval', args=(session, task), seconds=interval, id=name)

async def main():
    # 初始化调度器
    scheduler = AsyncIOScheduler()
    # 创建http会话
    async with aiohttp.ClientSession() as session:
        # 获取任务
        tasks = get_tasks_from_database()
        for task in tasks:
            # 解构任务
            name, _, _, _, _, _, _, interval, _ = task
            # 添加任务到调度器
            scheduler.add_job(monitor, 'interval', args=(session, task), seconds=interval, id=name)
        # 启动调度器
        scheduler.start()

        # 主循环
        while True:
            # 每分钟检查一次数据库
            await asyncio.sleep(10)
            new_tasks = get_tasks_from_database()
            new_task_names = {task[0] for task in new_tasks}
            old_task_names = {task[0] for task in tasks}

            # 查找新任务和被删除的任务
            added_tasks = [task for task in new_tasks if task[0] not in old_task_names]
            removed_tasks = [task for task in tasks if task[0] not in new_task_names]

            # 处理被删除的任务
            for task in removed_tasks:
                scheduler.remove_job(task[0])

            # 处理新任务
            for task in added_tasks:
                name, _, _, _, _, _, _, interval, _ = task
                scheduler.add_job(monitor, 'interval', args=(session, task), seconds=interval, id=name)

            # 查找被更新的任务
            for new_task in new_tasks:
                for old_task in tasks:
                    if new_task[0] == old_task[0] and new_task != old_task:
                        # 任务被更新，先删除旧任务，再添加新任务
                        scheduler.remove_job(old_task[0])
                        name, _, _, _, _, _, _, interval, _ = new_task
                        scheduler.add_job(monitor, 'interval', args=(session, new_task), seconds=interval, id=name)

            # 更新任务列表
            tasks = new_tasks

# 主程序入口
if __name__ == "__main__":
    asyncio.run(main())
