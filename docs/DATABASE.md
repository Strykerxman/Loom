### SQLAlchemy
--------------

A library for interacting with relational DBs in Python.  
It's an **Object-Relational Mapper** (ORM)  

**What does this mean:**  
- It allows devs to map database tables to Python classes.
- Data can be handled with standard Python objects, simplifying updating, creating and querying records.
- Provider agnostic.
- Has its own Python-based SQL expression language; use Python ops and functions to query data.
- Handles connection pooling and transactions automatically.

> SQLite database for early implementation, saves Postgres/Docker boilerplate.

### Alembic Migrations
--------------

Alembic owns database schema changes. The FastAPI app should not create tables on startup with `Base.metadata.create_all()` once migrations exist.

Core commands:

```bash
alembic upgrade head                  # apply migrations
alembic downgrade -1                  # roll back one migration
alembic revision --autogenerate -m "message"  # create a new migration from model changes
```

Migration files live in `alembic/versions/`. Each migration has an `upgrade()` and a `downgrade()` function.

The first Loom migration creates the current `jobs` and `tasks` tables. Future schema changes, such as task timestamps or provider metadata, should be added through new migrations.

Existing local databases created before Alembic need one of two paths:

- Reset the local Docker volume, then run `alembic upgrade head`.
- Keep the existing tables and run `alembic stamp head` to mark the current schema as already applied.

Use reset for disposable dev data. Use stamp when keeping existing local rows matters.

### Connection Pooling
--------------

[Resource Link](https://www.architecture-weekly.com/p/architecture-weekly-189-mastering)

**Brief:** Instead of creating new connections each time we want to access the database, it maintains a "pool" of available connections. The number of connections in the pool is initially fixed. When a query is completed, the connection is sent back to the pool for reuse. 

A pool can be resized dynamically (e.g., when demand exceeds the pre-defined number or when demand is low).  
**Result:** Reduces latency of creating new connections and boosts performance.

*Considerations:* pool size, connection timeout

Connections are stored in local memory. It's a data structure in the RAM. It stores the state (is a transaction open?, where is the cursor?).  
With SQLite, the database is a file on disk, not a remote server that can be connected to.

*New learning*: use the `with` keyword when a Worker accesses the database, i.e. `with SessionLocal() as db` instead of `db = SessionLocal()`. The idea is that a worker should open a session and close it when work is done. This returns the connection to the pool. The initial code (`db = SessionLocal()`) creates a connection and keeps it open, because the worker is still looking for pending tasks. It ensures that transactions with the database use a new, fresh connection instead of a possibly stale one from an hour ago.

### Sessions & Transaction Logic
--------------

A session is like a waiting room (a staging area in memory) for database operations. When doing `session.add(job_id)`, it does **NOT** immediately execute an `INSERT` statement; it sits in memory waiting to be executed.  

- `autocommit=False`: default; A session starts automatically but must be committed manually. `session.commit()` to save; `session.rollback()` to undo.
- ***autoflush=False*** (non-default): When True, SQLAlchemy will flush pending statements from memory before certain operations.

**Example:** If we run a `SELECT` query, SQLAlchemy will normally silently push (flush) pending changes first so the `SELECT` has up-to-date info.

**Pipeline Strategy:**
We want `autoflush=False` for full control. When generating 1,000 Task objects, we want to dump them in one massive sweep. This prevents SQLAlchemy from secretly flushing after each insert just because a read occurs mid-logic.

**Benefits:**
- Saves the hassle of rolling back specific `INSERT`s if an error occurs during payload building.
- Allows erasing the payload in memory to avoid leaving ***dead rows*** (old versions) and ***locks*** (preventing simultaneous transactions) in the database longer than needed.  

When we create an ***engine***, it allows a connection to a database and creates a pool (in most cases), as discussed above. It communicates with the database using a ***driver***, a "translator" that takes a request from, for example, a Python snippet and turns it into binary or specialized network packets that the database understands. The binary (or packets) is received by the database and bits are written directly to the disk.  

**ACID:**
- **Atomicity:** a transaction is successful or failed. Rolls back if deemed necessary.  
- **Consistency:** a transaction can only bring the database from one valid state to another. Respects `NOT NULL` or `UNIQUE` constraints.  
- **Isolation:** transactions can happen at the same time (or seemingly) and shouldn't interfere with each other.  
- **Durability:** 

### Adding, Committing, Refreshing

An entry is added to the stage, it gets committed and is then returned. [crud.py](app/database/crud.py)

```python
db.add(db_job) 
db.commit()
db.refresh(db_job)

return db_job
```  

Initially, `db_job.job_id = None` when it is created using `db_job = JobTable(...)`. It is then staged and committed. The Session translates the `JobTable` into `INSERT` SQL statements. They are then sent over the network to the database. The rows are inserted and the database autoincrements the primary key (i.e. the new job is given **ID 1** if it's the first insert). The Session does **NOT** automatically grab `job_id = 1` from the database, nor does it update the `db_job.job_id`.

SQLAlchemy has a default setting `expire_on_commit = True`, causing this behavior, the safest choice possible as SQLAlchemy doesn't know what the database did behind its back when inserting the new row, like giving an ID.

So there are expired attributes of data (i.e. `job_id`). How to update them instantly without having to create a new connection? A ***refresh*** is needed before closing the connection. This guarantees data is fetched while the Session is still open and it serves the updated data after it is committed (like a new `job_id`). SQLAlchemy runs a hidden `SELECT` when a refresh is called. It updates the affected Python objects. If there was no refresh, FastAPI would hand `db_job` to Pydantic (the `JobResponse` schema) and try to get `db_job.job_id`. It would then go into the database to find it, but it crashes as the Session is already closed.

### Concurrency

Before adding `with_for_update(skip_locked=True)` to a SQL query, workers query the database at the same moment and they each pick up the same task. This is inefficient, it is better to lock rows that a worker has picked up so the next workers do not also pick it up.
- `FOR UPDATE`: Locks a row.
- `SKIP LOCKED`: Moves to the next available, unlocked row.

The SQLAlchemy translation is `with_for_update(skip_locked=True)`. This turns the simple Python script into a robust, high-throughput distributed worker node.

### Cascading

When a Job is deleted, we want all of its Tasks to be deleted as well. This is called ***cascading deletes***. It prevents orphaned records (tasks without a parent job) and keeps the database clean. In SQLAlchemy, this is achieved by setting `cascade="all, delete-orphan"` in the relationship definition between Job and Task models. This means that when a Job is deleted, all associated Tasks will also be automatically deleted from the database. 

### Derived Job Status

`JobTable.status` is set to `pending` when a job is created. The API status endpoint does not rely only on that stored value.

The current status response is derived from related task rows:

- `pending`: no task has started.
- `running`: at least one task is running, done, or failed, but not all tasks are finished.
- `done`: all tasks are terminal, either `done` or `failed`.

A failed task does not automatically make the job failed. In Loom, task failure is evaluation data. Job status describes pipeline progress.

This means a job stuck at `pending` usually means no task moved out of `pending`. Debug worker startup, task claiming, and task state updates before changing `JobTable.status`.

