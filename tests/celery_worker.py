# celery_worker.py
from celery import Celery
import time
import os
import random
import requests # 用于模拟网络I/O

# 从 config.py 导入配置
from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# 初始化 Celery 应用
celery_app = Celery(
    'my_cloud_fastapi_app',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# 可选：配置 Celery
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Shanghai',
    enable_utc=True,
    worker_prefetch_multiplier=1 # <--- 这个设置是关键！
)

@celery_app.task(bind=True) # bind=True 允许任务访问自身实例 (self)
def process_data(self, data: dict):
    """
    一个模拟长时间运行的任务。
    """
    task_id = self.request.id
    print(f"[{os.getpid()}] Task {task_id}: Processing data: {data}...")
    total_steps = 10
    for i in range(total_steps):
        time.sleep(random.uniform(0.5, 1.5)) # 模拟随机耗时
        progress = (i + 1) * 100 // total_steps
        self.update_state(state='PROGRESS', meta={'current': i + 1, 'total': total_steps, 'progress': progress})
        print(f"[{os.getpid()}] Task {task_id}: Progress {progress}% for data {data['id']}")

    result = f"Processed data {data['id']} successfully. Result: {data['value'].upper()}"
    print(f"[{os.getpid()}] Task {task_id}: Finished for data: {data['id']}")
    return result

@celery_app.task
def send_email(to_email: str, subject: str, body: str):
    """
    模拟发送邮件的任务。
    """
    print(f"[{os.getpid()}] Sending email to {to_email} with subject: {subject}")
    time.sleep(3) # 模拟发送邮件
    print(f"[{os.getpid()}] Email sent to {to_email}")
    return f"Email to {to_email} sent successfully."


@celery_app.task
def io_intensive_task(task_name: str, delay_seconds: int = 2):
    """
    模拟一个 I/O 密集型任务，例如等待网络响应。
    """
    pid = os.getpid()
    print(f"[{pid}] [IO Task START] {task_name} - Simulating network request...")
    # 模拟网络请求，这是一个阻塞的 I/O 操作
    # time.sleep(delay_seconds) # 也可以用time.sleep来模拟，但requests更接近真实网络I/O
    try:
        # 使用一个可靠的、响应较快的外部API进行测试，或者用time.sleep模拟
        # response = requests.get(f"https://httpbin.org/delay/{delay_seconds}", timeout=delay_seconds + 5)
        time.sleep(delay_seconds) # 简化为time.sleep方便观察
        # print(f"[{pid}] [IO Task] {task_name} - Response status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[{pid}] [IO Task ERROR] {task_name} - Request failed: {e}")
        raise
    print(f"[{pid}] [IO Task END] {task_name} - Finished after {delay_seconds} seconds.")
    return f"IO Task {task_name} completed."

@celery_app.task
def cpu_intensive_task(task_name: str, iterations: int = 10**7):
    """
    模拟一个 CPU 密集型任务，例如进行大量计算。
    """
    pid = os.getpid()
    print(f"[{pid}] [CPU Task START] {task_name} - Performing heavy calculations...")
    result = 0
    for i in range(iterations):
        result += i * i % 7 # 模拟一些计算
    print(f"[{pid}] [CPU Task END] {task_name} - Calculation finished. Final result: {result}.")
    return f"CPU Task {task_name} completed. Result: {result}"