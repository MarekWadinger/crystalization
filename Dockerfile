# CPU image — works on any machine, no GPU required.
#
# GPU alternative: replace the FROM line with:
#   FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
#   RUN apt-get update && apt-get install -y python3.10 python3-pip \
#       && ln -s /usr/bin/python3.10 /usr/bin/python
# Then add --gpus all to your docker run command.

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Saves result as .jpg instead of opening an interactive window
ENV MPLBACKEND=Agg

ENTRYPOINT ["python", "analyze_crystals.py"]