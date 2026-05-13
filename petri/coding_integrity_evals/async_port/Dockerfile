FROM python:3.11-slim

RUN pip install --no-cache-dir requests aiosqlite httpx aiofiles pytest pytest-asyncio

COPY userservice/ /app/
WORKDIR /app
