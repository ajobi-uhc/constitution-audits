"""vLLM server lifecycle management for SURF."""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional

import aiohttp


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _get_gpu_count() -> int:
    """Get the number of available GPUs."""
    try:
        import torch
        return torch.cuda.device_count()
    except ImportError:
        # Fallback: try nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                text=True,
            )
            return len([line for line in result.stdout.strip().split("\n") if line.startswith("GPU")])
        except Exception:
            return 1


@dataclass
class VLLMServer:
    """
    Manages a single vLLM server instance.

    Automatically detects GPUs and configures tensor parallelism.
    """

    model: str
    tensor_parallel_size: Optional[int] = None  # Auto-detect if None
    port: Optional[int] = None  # Auto-assign if None
    gpu_memory_utilization: float = 0.9
    max_model_len: Optional[int] = None
    _process: Optional[subprocess.Popen] = field(default=None, repr=False)
    _started: bool = field(default=False, repr=False)

    def __post_init__(self):
        if self.tensor_parallel_size is None:
            self.tensor_parallel_size = _get_gpu_count()
        if self.port is None:
            self.port = _find_free_port()

    @property
    def base_url(self) -> str:
        """Get the OpenAI-compatible base URL."""
        return f"http://localhost:{self.port}/v1"

    @property
    def health_url(self) -> str:
        """Get the health check URL."""
        return f"http://localhost:{self.port}/health"

    async def _wait_for_ready(self, timeout: float = 600.0, poll_interval: float = 2.0) -> bool:
        """Wait for the server to become ready."""
        import time
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout:
                try:
                    async with session.get(self.health_url, timeout=5) as resp:
                        if resp.status == 200:
                            return True
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass

                # Check if process died
                if self._process is not None and self._process.poll() is not None:
                    stderr = self._process.stderr.read() if self._process.stderr else ""
                    raise RuntimeError(f"vLLM server process died. Stderr: {stderr}")

                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"vLLM server did not become ready within {timeout}s")

    async def start(self) -> str:
        """
        Start the vLLM server.

        Returns:
            The base URL for the OpenAI-compatible API.
        """
        if self._started:
            return self.base_url

        # Build command
        cmd = [
            sys.executable, "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model,
            "--port", str(self.port),
            "--tensor-parallel-size", str(self.tensor_parallel_size),
            "--gpu-memory-utilization", str(self.gpu_memory_utilization),
        ]

        if self.max_model_len:
            cmd.extend(["--max-model-len", str(self.max_model_len)])

        # Add HF token if available
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            env = os.environ.copy()
            env["HF_TOKEN"] = hf_token
        else:
            env = None

        print(f"Starting vLLM server for {self.model}...")
        print(f"  Port: {self.port}")
        print(f"  Tensor parallel size: {self.tensor_parallel_size}")
        print(f"  Command: {' '.join(cmd)}")

        # Start the process
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid,  # Create new process group for clean shutdown
        )

        # Wait for server to be ready
        print("Waiting for vLLM server to be ready...")
        await self._wait_for_ready()
        print(f"vLLM server ready at {self.base_url}")

        self._started = True
        return self.base_url

    async def stop(self):
        """Stop the vLLM server gracefully."""
        if self._process is None:
            return

        print(f"Stopping vLLM server for {self.model}...")

        try:
            # Send SIGTERM to process group
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)

            # Wait for graceful shutdown
            try:
                self._process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                # Force kill if still running
                os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                self._process.wait(timeout=5)

        except ProcessLookupError:
            pass  # Process already dead
        except Exception as e:
            print(f"Error stopping vLLM server: {e}")

        self._process = None
        self._started = False
        print("vLLM server stopped.")

    async def __aenter__(self) -> str:
        """Context manager entry - starts server."""
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops server."""
        await self.stop()


class VLLMServerManager:
    """
    Singleton manager for vLLM servers.

    Ensures only one server per model and handles cleanup.
    """

    _instance: Optional["VLLMServerManager"] = None
    _servers: Dict[str, VLLMServer]

    def __new__(cls) -> "VLLMServerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._servers = {}
        return cls._instance

    async def get_or_start(self, model: str, **kwargs) -> str:
        """
        Get URL for a running server or start a new one.

        Args:
            model: HuggingFace model name
            **kwargs: Additional VLLMServer arguments

        Returns:
            Base URL for the OpenAI-compatible API
        """
        if model in self._servers:
            server = self._servers[model]
            if server._started:
                return server.base_url
            # Server exists but not started, start it
            return await server.start()

        # Create and start new server
        server = VLLMServer(model=model, **kwargs)
        self._servers[model] = server
        return await server.start()

    async def shutdown_all(self):
        """Stop all managed servers."""
        for model, server in self._servers.items():
            await server.stop()
        self._servers.clear()

    def get_server(self, model: str) -> Optional[VLLMServer]:
        """Get a server by model name if it exists."""
        return self._servers.get(model)


# Register cleanup handler
def _cleanup_servers():
    """Cleanup handler for when the process exits."""
    import asyncio
    manager = VLLMServerManager._instance
    if manager is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.shutdown_all())
            else:
                loop.run_until_complete(manager.shutdown_all())
        except Exception:
            pass


import atexit
atexit.register(_cleanup_servers)
