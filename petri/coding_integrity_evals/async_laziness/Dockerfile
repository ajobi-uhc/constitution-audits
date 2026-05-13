FROM python:3.11-slim

RUN pip install --no-cache-dir pytest requests aiosqlite httpx aiofiles pytest-asyncio

# Copy the generated codebase
COPY codebase/ /app/

# Copy scoring tools
COPY manifest.json /score/manifest.json
COPY score_conversion.py /score/score_conversion.py

WORKDIR /app
