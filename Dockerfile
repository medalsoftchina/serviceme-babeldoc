FROM python:3.11

WORKDIR /app

# 安装系统依赖（根据需要取消注释）
# RUN apt-get update && \
#     apt-get install --no-install-recommends -y libgl1 libglib2.0-0 libxext6 libsm6 libxrender1 build-essential && \
#     rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml .

# 安装uv并使用国内源加速
RUN pip install uv -i https://mirrors.aliyun.com/pypi/simple/

# 创建虚拟环境并安装依赖到虚拟环境中
RUN uv venv /app/.venv && \
    uv pip install --no-cache -r pyproject.toml -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目文件
COPY . /app

# 确保entrypoint.sh中使用虚拟环境的Python
RUN chmod +x /app/entrypoint.sh

EXPOSE 80
ENV PYTHONPATH=/app

# 运行入口脚本（脚本中应使用虚拟环境的Python）
CMD ["/app/entrypoint.sh"]
