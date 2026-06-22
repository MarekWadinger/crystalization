# CPU image — works on any machine, no GPU required. Analyze only (no GUI/training).
# Build from the repo root:  docker build -f src/crystal_detector/Dockerfile -t crystal-analyzer .
#
# GPU alternative: replace the FROM line with:
#   FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
#   RUN apt-get update && apt-get install -y python3 python3-pip && ln -s /usr/bin/python3 /usr/bin/python
# Then add --gpus all to your docker run command.

FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# uv for dependency resolution from the project's dependency group.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY src/crystal_detector ./src/crystal_detector
RUN uv sync --group crystal-detector --no-dev

# Saves result as .jpg instead of opening an interactive window.
ENV MPLBACKEND=Agg

ENTRYPOINT ["uv", "run", "crystal-detector-analyze"]
