# 使用官方 Python 3.10 镜像
FROM python:3.10-slim

# 安装项目依赖
RUN pip install diglife -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip show diglife | grep Version 
# 暴露应用运行的端口
EXPOSE 80

# 设置默认命令启动 FastAPI 应用
CMD ["python", "-m", "stkweight.server","80","--prod"]


# docker build -t your-python-app:latest .  

# docker run -p 8000:80 your-python-app:latest

# docker run --rm diglife-diglife sh -c "pip show diglife | grep Version"