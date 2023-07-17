# lite-apimonitor 接口监控告警程序

## 描述

这是一个使用Python编写的异步接口监控系统。该项目通过定时向目标API发送HTTP请求，并根据响应结果执行特定的操作。如果响应结果与预期不符，系统将通过钉钉机器人发送告警消息。
主打一个功能实现，作者是个小白欢迎巨佬pr
该项目主要使用了以下库：

- `aiohttp`处理异步HTTP请求。
- `AsyncIOScheduler`进行定时任务。
- `sqlite3`用于从SQLite数据库中获取任务信息。
- `DingtalkChatbot`用于发送告警消息至钉钉群。
- `fastapi`用于给监控任务提供web接口初步实现增删查改。

## 功能

- 异步网络请求
- 支持 GET/POST 请求
- 支持预期的响应状态码和响应中的特定关键字
- 钉钉群告警

## 使用指南

首先，需要初始化SQLite数据库和一个钉钉群机器人。

数据库中需要有一个名为 "tasks" 的表，包含下列字段：

- name（任务名）
- method（get/post）
- url
- headers
- params
- timeout
- status_code（预期响应状态码）
- interval（请求间隔时间，单位为秒）
- keyword（预期响应中包含的关键字)

钉钉机器人需要启用 "自定义关键字" 触发方式，钉钉群机器人的 "安全设置" 中需添加一个自定义关键字例如 "通知"。

安装好所有依赖后，使用以下命令即可运行：

```bash
#启动 web_api 
#启动前请确保main.py 与 monitor_api.py 中sqlite文件为同一个
python monitor_api.py
#添加监控任务 参数说明见上面数据库字段说明
#监控程序不依赖web_api，web_api只提供一个使用接口的方式提供监控程序的监控任务的增删改查下面是一个添加任务的例子，其他的使用方法请运行monitor_api.py后访问http://127.0.0.1:8000/docs 进行查看修改删除等操作
curl -X 'POST' \
  'http://127.0.0.1:8000/tasks/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
"name": "local2",
  "method": "POST",
  "url": "http://127.0.0.1:8081",
  "headers": "{\"Content-Type\": \"application/json\"}",
  "params": "{\"name\": \"zhangsan\"}",
  "timeout": 10,
  "status_code": 200,
  "interval": 300,
  "keyword": "ok"
}'

#运行监控程序 运行前如果需要钉钉的通知需提前准备钉钉hook机器人 并修改main.py 中机器人的地址
python main.py

