import sys
import time
import subprocess
import threading
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO


@dataclass # saves boiler plate like __init__, __eq__, etc.
class WorkerHandle:
    """
    Represents one spawned worker process along with the resources used to monitor it.
    
    Removes the need to track indices when looping through workers.
    """

    process: subprocess.Popen
    log_path: Path | None
    monitor_threads: list[threading.Thread]

def _timestamp(for_filename: bool | None = None):
    from datetime import datetime

    if for_filename:
        return datetime.now().strftime("%Y-%m-%d_%H%M")

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _project_root() -> Path:
    # scripts/worker_utils.py -> scripts -> repo root
    return Path(__file__).resolve().parents[1]


def _logs_dir(root_dir: Path) -> Path:
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _worker_env(root_dir: Path) -> dict[str, str]:
    """
    Build the environment variables for a worker subprocess.
    
    Requirements:
    - copy parent process env
    - force unbuffered Python output
    - force utf-8 output
    - prepend project root to PYTHONPATH
    """
    env = os.environ.copy()
    # env.setdefault("PYTHONUNBUFFERED", "1") !!already covered by `-u` in _worker_command below!!
    env.setdefault("PYTHONIOENCODING", "utf-8") # ensures emojis are properly parsed
    env["PYTHONPATH"] = str(root_dir) + os.pathsep + env.get("PYTHONPATH", "")

    return env


def _worker_command(flags: list[str] | None = None) -> list[str]:
    """
    Return the command used to launch one (1) worker.

    * Kept in one place so future changes are easy, e.g. switching from:
        `python -m app.worker`
    to:
        `python -m app.worker --some-flag`
    """
    command = [sys.executable, "-u", "-m", "app.worker",] 

    if flags:
        command.extend(f"--{flag}" for flag in flags)

    return command


def _worker_log_path(logs_dir: Path, worker_idx: int) -> Path:
    """
    Return a unique log path for one (1) worker.

    Requirements:
    - current timestamp or epoch seconds
    - worker index

    Example: logs/worker_1778516492_1.log
    """
    return logs_dir / f"worker_{_timestamp(for_filename=True)}_{worker_idx}.log"

# an asterisk in a method signature indicates that the following params MUST be passed as keywords, not by position
# benefits are clarity, but can lead to verbosity
def _pump_stream(
    stream: TextIO,
    *,
    log_path: Path | None,
    worker_label: str,
    stream_name: str,
    mirror_to_console: bool
) -> None:
    """
    Read lines from one subprocess stream until end-of-file (EOF).

    This function owns reading from the stream. There must not be another thread reading the same stream.
    """
    log_file = None

    try:
        if log_path is not None:
            log_file = open(log_path, "a", encoding="utf-8") 

        for line in iter(stream.readline, ""):
            if not line:
                break

            formatted = f"[{_timestamp()}] [{worker_label}] [{stream_name}] {line}"

            if log_file is not None:
                log_file.write(formatted)
                log_file.flush()
            
            if mirror_to_console:
                print(formatted, end="")

    except Exception:
        pass # we do not want logging failure to crash the whole run

    finally:
        if log_file is not None:
            log_file.close()


def _start_stream_pump(
    stream: TextIO,
    *,
    log_path: Path | None,
    worker_label: str,
    stream_name: str,
    mirror_to_console: bool,
) -> threading.Thread:
    """
    Start one daemon thread that pumps oen subprocess stream.

    Note to self: This function should not contain the stream-reading logic itself.
    It only wires arguments `_pump_stream()` and starts the thread.
    """
    thread = threading.Thread(
        target=_pump_stream,
        kwargs={
            "stream": stream,
            "log_path": log_path,
            "worker_label": worker_label,
            "stream_name": stream_name,
            "mirror_to_console": mirror_to_console
        },
        daemon=True,
    )

    thread.start()
    return thread


def spawn_worker(
    worker_idx: int,
    *,
    capture_logs: bool = True,
    stream_to_console: bool = False,
) -> WorkerHandle:
    
    root_dir = _project_root()
    log_path = None

    if capture_logs:
        log_path = _worker_log_path(_logs_dir(root_dir), worker_idx)

    process = subprocess.Popen(
        _worker_command(),
        stdout=subprocess.PIPE if capture_logs else None,
        stderr=subprocess.PIPE if capture_logs else None,
        text=True,
        bufsize=1,
        env=_worker_env(root_dir),
        cwd=str(root_dir)
    )

    monitor_threads: list[threading.Thread] = []

    if capture_logs:
        assert process.stdout is not None
        assert process.stderr is not None

        worker_label = f"worker-{process.pid}"

        monitor_threads.append(
            _start_stream_pump(
                process.stdout,
                log_path=log_path,
                worker_label=worker_label,
                stream_name="OUT",
                mirror_to_console=stream_to_console,
            )
        )

        monitor_threads.append(
            _start_stream_pump(
                process.stderr,
                log_path=log_path,
                worker_label=worker_label,
                stream_name="ERR",
                mirror_to_console=stream_to_console,
            )
        )

    return WorkerHandle(
        process=process,
        log_path=log_path,
        monitor_threads=monitor_threads,
    )


def spawn_workers(
    n: int,
    *,
    capture_logs: bool = True, 
    stream_to_console: bool = False
) -> list[WorkerHandle]:
    """Spawn n worker subprocesses.
    """
    if n <= 0:
        raise ValueError("n must be a greater than 0")
    
    workers: list[WorkerHandle] = []

    for idx in range(1, n + 1):
        worker = spawn_worker(
            idx,
            capture_logs=capture_logs,
            stream_to_console=stream_to_console,
        )
        workers.append(worker)

        time.sleep(0.1)
    
    return workers


def stop_worker(
    worker: WorkerHandle,
    *,
    timeout_seconds: float = 2.0,
) -> None:
    """
    Stops one worker process gracefully
    """
    # Clean up steps
    # 1. politely ask to stop
    # 2. wait for it to try to stop
    # 3. forcefully stop if doesnt work
    # 4. wait for it to forcefully stop
    # 5. clean up threads
    worker_proc: subprocess.Popen = worker.process
    monitor_threads: list[threading.Thread] = worker.monitor_threads
    
    try:
        if worker_proc.poll() is None:
            worker_proc.terminate()
        
        worker_proc.wait(timeout=timeout_seconds)

    except subprocess.TimeoutExpired:
        worker_proc.kill()
        try: # nested because kill + wait may also fail
            worker_proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            print(f"Worker {worker_proc.pid} did not exit after kill()")
        # wait to give time to OS to kill it and return exit code


    except Exception as e:
        print(f"Failed to stop worker {worker_proc.pid}: {e}")
        
    finally:
        for thread in monitor_threads:
            if thread.is_alive():
                thread.join(timeout=0.2)


def stop_workers(
    workers: Iterable[WorkerHandle]
) -> None:
    for worker in workers:
        try:
            stop_worker(worker)
        except Exception as e:
            print(f"Failed to stop worker {worker.process.pid} in final loop: {e}")