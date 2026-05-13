# Logging

## Log boundaries

Worker logs belong to the child worker process. Harness logs belong to the parent process that spawns and stops workers.

Do not mix these sources by default.

| Source | Example file | Contains |
|:--|:--|:--|
| Worker process | `logs/worker_2026-05-12_2145_1.log` | Worker `stdout` and `stderr` |
| Harness process | `logs/worker_harness.log` | Spawn, stop, and cleanup errors |
| Test runner | Console | Test progress and assertions |

Current Loom worker helpers write child process output to per-worker files. Harness cleanup errors are printed to the parent console.

## Standard output and standard error

`stdout` is normal process output. `stderr` is diagnostic or error output.

When a worker is spawned with `subprocess.Popen(..., stdout=PIPE, stderr=PIPE)`, the parent process must read both streams. If it does not, pipe buffers can fill and block the child process.

## One reader per stream

Each pipe must have one reader.

Bad pattern:

```python
# Two threads read the same pipe. Lines are split unpredictably.
thread_1_reads(process.stdout)
thread_2_reads(process.stdout)
```

Correct pattern:

```python
# One thread reads the pipe and fans out the line.
read_stdout_once_then_write_to_file_and_console()
```

A stream pump should read one line, format it once, then write it to all enabled destinations.

## Log file ownership

A worker log file is opened by the parent harness, but it contains child worker output. Prefix each line with enough context to make the source clear.

Recommended fields:

```text
[timestamp] [worker-pid] [OUT|ERR] message
```

Example:

```text
[2026-05-12 21:45:45] [worker-18084] [OUT] Worker started. Listening for tasks...
```

## Optional log files

When a file is optional, initialise the variable to `None` before conditional creation.

Pattern:

```python
log_file = None

if log_path is not None:
    log_file = open(log_path, "a", encoding="utf-8")
```

`None` means no file is open. Later checks can safely use `if log_file is not None` without risking an unbound local variable.

## Console mirroring

Console mirroring is useful while debugging. It should reuse the same stream reader that writes the log file.

Do not create a second reader just to print to the console. That creates competing readers on the same pipe.

## Buffering

Python buffers output by default. A worker may print a line but not flush it immediately.

Loom launches workers with `-u`:

```text
python -u -m app.worker
```

`-u` enables unbuffered binary stdout and stderr. This helps parent monitor threads receive worker output promptly.

## Encoding

Windows consoles can use legacy encodings that fail on Unicode output. Worker subprocesses should force UTF-8 output.

Current environment setting:

```text
PYTHONIOENCODING=utf-8
```

Worker code can also reconfigure `stdout` and `stderr` when needed.

## Logging failure policy

Logging should not crash the test harness. Stream pumps are development infrastructure, not product logic.

Policy:

- If writing a log line fails, stop or skip logging.
- If cleanup logging fails, print a short parent-console message.
- Do not hide application errors inside worker code.

## Future direction

The application should eventually use structured logging instead of raw `print()` calls.

Useful fields:

| Field | Purpose |
|:--|:--|
| `job_id` | Connect events to an evaluation job. |
| `task_id` | Trace one task through claim, run, retry, and completion. |
| `worker_pid` | Identify the worker process. |
| `status_from` / `status_to` | Track state transitions. |
| `retry_count` | Explain repeated attempts. |
| `error_class` | Group failure types. |
| `latency_ms` | Measure provider and evaluator time. |

Keep worker output and harness output separate even after structured logging is added.
