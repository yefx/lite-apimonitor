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

def find_token(d, key):
    if key in d:
        return d[key]
    for k in d:
        if isinstance(d[k], list):
            for i in d[k]:
                if isinstance(i, dict):
                    if find_token(i, key) is not None:
                        return find_token(i, key)
        elif isinstance(d[k], dict):
            if find_token(d[k], key) is not None:
                return find_token(d[k], key)
    return None

# 定义异步监控函数
async def monitor(session, task):
    # 解构任务
    name, method, url, headers, params, timeout, status_code, interval, keyword, login, login_name = task
    try:
        # 输出任务信息
        logging.info(f"执行任务: {name}, URL: {url}, headers: {headers}, params: {params}")

        if headers is None or headers == '':
            headers = {}
        else:
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                headers = {}

        if params is None or params == '':
            params = {}
        else:
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                params = {}

        if login:
            # 获取认证信息
            auth_info = get_auth_info_from_database(login_name)
            if auth_info is not None:
                login_url, login_method, login_headers, login_params = auth_info
                if login_headers is None or login_headers == '':
                    login_headers = {}
                else:
                    try:
                        login_headers = json.loads(login_headers)
                    except json.JSONDecodeError:
                        login_headers = {}

                if login_params is None or login_params == '':
                    login_params = {}
                else:
                    try:
                        login_params = json.loads(login_params)
                    except json.JSONDecodeError:
                        login_params = {}
                # 认证步骤
                if login_method.lower() == 'get':
                    login_response = await session.get(login_url, headers=login_headers, params=login_params)
                else:
                    login_response = await session.post(login_url, headers=login_headers, data=login_params)
                login_response_text = await login_response.text()
                response_data = json.loads(login_response_text)
                token = find_token(response_data, 'token')
                # 在headers中添加token
                headers['Authorization'] = f'Bearer {token}'

        # 根据请求方法执行请求
        if method.lower() == 'get':
            response = await session.get(url, headers=headers, params=params, timeout=timeout)
        else:
            response = await session.post(url, headers=headers, data=params, timeout=timeout)
        text = await response.text()
        # 判断响应状态和关键词
        if response.status != status_code or keyword not in text:
            # 构造告警信息
            now_time = get_current_time()
            msg = f"警告-响应错误\n\n时间： {now_time}\n\n监控: {name}\n\n正常值：{status_code}-{keyword}\n\n响应状态码：{response.status}\n\n响应信息: {text}\n\n"
            send_dingbot(msg)
            logging.error(f"警告-响应错误 时间： {now_time} 监控: {name} 正常值：{status_code}-{keyword} 响应状态码：{response.status} 响应信息: {text}\n")
    except aiohttp.ClientError as e:
        # 发送异常信息
        now_time = get_current_time()
        msg = f"警告-响应错误\n\n时间： {now_time}\n\n监控: {name}\n\n正常值：{status_code}-{keyword}\n\n响应信息: {str(e)}\n\n"
        send_dingbot(msg)
        logging.error(msg)


def get_auth_info_from_database(task_name):
    try:
        # 连接到 SQLite 数据库
        conn = sqlite3.connect(DATAFILE_PATH)
        cursor = conn.cursor()

        # 从 auth_info 表获取认证信息
        cursor.execute(
            'SELECT login_url, login_method, login_headers, login_params FROM auth_info WHERE task_name = ?',
            (task_name,)
        )
        auth_info = cursor.fetchone()
        cursor.close()
        conn.close()
    except sqlite3.OperationalError as e:
        logging.error(f"数据库操作错误: {str(e)}")
        return None  # 返回None, 因为无法获取认证信息

    return auth_info

# 从数据库中获取任务
def get_tasks_from_database():
    try:
        cursor.execute("""
            SELECT name, method, url, headers, params, timeout, status_code, interval, keyword, login, login_name
            FROM tasks""")
        tasks = cursor.fetchall()
    except sqlite3.OperationalError:
        logging.error(f"数据库操作错误: {str(e)}")
        return {}

    # 使用列表裹字典推导式优化处理 headers 和 params 的逻辑
    tasks = {
        task_name: {
            'method': method,
            'url': url,
            'headers': json.loads(headers) if headers else {},
            'params': json.loads(params) if params else {},
            'timeout': timeout,
            'status_code': status_code,
            'interval': interval,
            'keyword': keyword,
            'login': login,
            'login_name': login_name if login_name else ''
        }
        for task_name, method, url, headers, params, timeout, status_code, interval, keyword, login, login_name in tasks
    }

    return tasks

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

def get_tasks_from_database():
    try:
        # 判断 tasks 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
        if cursor.fetchone() is None:
            raise sqlite3.OperationalError("数据库中'tasks'表不存在,或者未添加任务监控程序不执行")

        # 从 tasks 表获取任务数据
        cursor.execute(
            'SELECT name, method, url, headers, params, timeout, status_code, interval, keyword, login, login_name FROM tasks'
        )
        tasks = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"数据库操作错误: {str(e)}")
        return {}  # 返回空字典, 因为无法获取任务

    # 解析 headers 和 params
    for task in tasks:
        task = list(task)  # 将元组转换为列表
        if task[3] is None or task[3] == '':
            task[3] = {}  # headers
        else:
            try:
                task[3] = json.loads(task[3])
            except json.JSONDecodeError:
                task[3] = {}
        if task[4] is None or task[4] == '':
            task[4] = {}
        else:
            try:
                task[4] = json.loads(task[4])
            except json.JSONDecodeError:
                task[4] = {}
        if task[10] is None:
            task[10] = ''
        task = tuple(task)

    return {task[0]: task for task in tasks}


async def main():
    # 初始化调度器
    scheduler = AsyncIOScheduler()
    # 创建http会话
    async with aiohttp.ClientSession() as session:
        # 获取任务
        tasks = get_tasks_from_database()
        for name, task in tasks.items():
            # 解构任务
            _, _, _, _, _, _, _, interval, _, _, _ = task
            # 添加任务到调度器
            scheduler.add_job(monitor, 'interval', args=(session, task), seconds=interval, id=name)
        # 启动调度器
        scheduler.start()

        # 主循环
        while True:
            # 每分钟检查一次数据库
            await asyncio.sleep(60)
            new_tasks = get_tasks_from_database()

            # 查找新任务和被删除的任务
            added_tasks = {name: task for name, task in new_tasks.items() if name not in tasks}
            removed_tasks = {name: task for name, task in tasks.items() if name not in new_tasks}

            # 处理被删除的任务
            for name in removed_tasks:
                scheduler.remove_job(name)

            # 处理新任务和被更新的任务
            for name, task in added_tasks.items():
                _, _, _, _, _, _, _, interval, _, _, _ = task
                scheduler.add_job(monitor, 'interval', args=(session, task), seconds=interval, id=name)

            # 更新任务列表
            tasks = new_tasks

# 主程序入口
if __name__ == "__main__":
    # 数据库sqlite文件
    DATAFILE_PATH = 'apimonitor.db'
    # 连接到 SQLite 数据库
    with sqlite3.connect(DATAFILE_PATH) as conn:
        cursor = conn.cursor()
        asyncio.run(main())

