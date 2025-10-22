# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

import random # 用于生成随机数据
from typing import Dict
from celery.result import AsyncResult
from celery_worker import celery_app # 导入 celery_app 实例用于 AsyncResult
from celery_worker import process_data, send_email, io_intensive_task, cpu_intensive_task


app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to FastAPI with Cloud Celery Queue!"}

@app.post("/tasks", status_code=202) # 使用 202 Accepted 表示请求已接受但未完成
async def create_task(data: Dict):
    """
    POST 方法：创建并提交一个后台任务到 Celery 队列。
    请求体示例: {"id": 1, "value": "some_data"}
    """
    if not isinstance(data, dict) or "id" not in data or "value" not in data:
        raise HTTPException(status_code=400, detail="Invalid data format. Expected {'id': int, 'value': str}")

    # 提交任务到 Celery 队列
    task = process_data.delay(data) # .delay() 是 Celery 任务的快捷方式
    print(f"Task submitted with ID: {task.id}")
    return JSONResponse(
        {"message": "Task submitted successfully!", "task_id": task.id},
    )

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    GET 方法：获取指定任务的状态和结果。
    """
    # AsyncResult 需要 Celery app 实例来查询结果
    task_result = AsyncResult(task_id, app=celery_app) # 使用导入的 celery_app 实例

    # 获取任务状态
    status = task_result.status

    response_data = {
        "task_id": task_id,
        "status": status,
        "result": None,
        "progress": None,
        "error": None
    }

    if status == 'PENDING':
        # 任务还未开始处理
        response_data["message"] = "Task is pending or unknown."
    elif status == 'STARTED':
        # 任务已开始处理
        response_data["message"] = "Task has started."
    elif status == 'PROGRESS':
        # 任务正在进行中，并且有进度信息
        if task_result.info and isinstance(task_result.info, dict):
            response_data["progress"] = task_result.info.get('progress')
            response_data["message"] = f"Task in progress: {response_data['progress']}%"
        else:
            response_data["message"] = "Task in progress."
    elif status == 'SUCCESS':
        # 任务成功完成
        response_data["result"] = task_result.result
        response_data["message"] = "Task completed successfully."
    elif status == 'FAILURE':
        # 任务执行失败
        response_data["error"] = str(task_result.info)
        response_data["message"] = "Task failed."
        return JSONResponse(response_data, status_code=500) # 失败的任务返回 500

    return JSONResponse(response_data)


@app.post("/send_email_task", status_code=202)
async def trigger_email_task(to_email: str, subject: str, body: str):
    """
    触发一个发送邮件的后台任务。
    """
    task = send_email.delay(to_email, subject, body)
    return JSONResponse(
        {"message": "Email sending task submitted.", "task_id": task.id},
    )

# 示例：快速生成测试数据
@app.post("/generate_test_tasks/{count}", status_code=202)
async def generate_test_tasks(count: int):
    task_ids = []
    for i in range(count):
        data = {"id": i + 1, "value": f"test_data_{random.randint(1000, 9999)}"}
        task = process_data.delay(data)
        task_ids.append(task.id)
    return {"message": f"{count} test tasks generated.", "task_ids": task_ids}


@app.post("/io_task/{name}", status_code=202)
async def submit_io_task(name: str, delay: int = 2):
    """提交一个 I/O 密集型任务。"""
    task = io_intensive_task.delay(name, delay)
    return JSONResponse(
        {"message": f"IO task '{name}' submitted.", "task_id": task.id},
    )

@app.post("/cpu_task/{name}", status_code=202)
async def submit_cpu_task(name: str, iterations: int = 10**7):
    """提交一个 CPU 密集型任务。"""
    task = cpu_intensive_task.delay(name, iterations)
    return JSONResponse(
        {"message": f"CPU task '{name}' submitted.", "task_id": task.id},
    )