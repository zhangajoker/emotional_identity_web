FROM python:3.10-slim

WORKDIR /app
ENV PIP_DEFAULT_TIMEOUT=120

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# CUDA PyTorch must be installed before Ultralytics so pip does not
# resolve a CPU-only build from the default index.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    --index-url https://download.pytorch.org/whl/cu121 \
    torch==2.1.1 \
    torchvision==0.16.1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    --retries 5 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
