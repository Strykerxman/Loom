### Big picture

A thread is a sequence of instructions scheduled by the operating system inside one process. Threads in the same process share memory, including Python objects, module state, and open file handles.

Threads are useful when work waits on input or output, such as database queries, network calls, file writes, or subprocess output. While one thread waits, another can run.

### Threads vs processes

| Concept | Thread | Process |
|:--|:--|:--|
| Memory | Shared with other threads in the process | Separate memory space |
| Creation cost | Lower | Higher |
| Failure isolation | Lower | Higher |
| Loom use | Reading worker stdout/stderr | Running workers |

Loom worker helpers spawn workers as separate processes with `subprocess.Popen`. The parent test harness uses threads only to read each child process stream.

### Why `worker_utils.py` uses threads

A worker process can write to both `stdout` and `stderr`. If the parent process does not read those pipes, output can block once the pipe buffer fills.

The harness starts one thread for `stdout` and one thread for `stderr`. Each thread reads one stream and writes lines to a log file, the console, or both.

Rule: one pipe gets one reader. Do not start two threads reading the same `stdout` or `stderr` stream, because they will steal lines from each other.

### Subprocess handles

`subprocess.Popen` returns a handle to a child process. The handle does not contain the worker logic. It gives the parent process control over the child lifecycle.

Useful methods and attributes:

| API | Meaning |
|:--|:--|
| `poll()` | Return `None` if the process is still running, otherwise return the exit code. |
| `terminate()` | Ask the process to stop. This is the polite shutdown step. |
| `wait(timeout=...)` | Wait for the process to exit. Raises `TimeoutExpired` if it takes too long. |
| `kill()` | Force the process to stop. Use after `terminate()` times out. |
| `returncode` | Exit code after the process exits. Usually `None` while running. |
| `pid` | Operating system process ID. Useful in logs and diagnostics. |

### Worker shutdown pattern

Shutdown is best-effort cleanup. It should not crash the test runner.

Expected flow:

1. Check if the process is alive with `poll()`.
2. If alive, call `terminate()`.
3. Wait briefly with `wait(timeout=...)`.
4. If waiting times out, call `kill()`.
5. Wait briefly again.
6. Join monitor threads so logs can flush.

If the second wait fails after `kill()`, give up cleanly. The parent has already attempted polite and forceful shutdown.

### Thread joins

`thread.join(timeout=...)` waits for a thread to finish. It does not kill the thread.

Monitor threads naturally finish when the child process exits and its pipes close. Joining briefly gives them time to write the last log lines.

Daemon threads do not block Python from exiting. They are useful for monitoring tasks that should not keep the test process alive forever.

**What are daemons?:** Daemon threads are background threads that do not prevent the program from exiting. They are useful for monitoring tasks that should not keep the test process alive forever. In Loom, monitor threads can be set as daemons so that if they fail to join during cleanup, they won't block the test runner from exiting.

### Shared memory and database access

Threads share process memory. This is efficient, but shared mutable state can cause race conditions.

Database connection pools reduce shared-connection problems by handing out separate connection objects. A busy connection is not reused until it is returned to the pool.

SQLite allows only limited concurrent writes. PostgreSQL handles concurrent readers and writers more effectively through server-side process management and row-versioning behaviour.

### Loom rules

- Use processes for workers.
- Use threads for pipe monitoring.
- Use one reader per pipe.
- Keep `WorkerHandle` as the owner of process, log path, and monitor threads.
- Keep singular and plural helpers separate: `spawn_worker()` owns one worker, `spawn_workers()` loops.
- Keep cleanup best-effort. Tests should fail because assertions fail, not because cleanup crashed.
