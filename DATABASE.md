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

### Connection Pooling
--------------

[Resource Link](https://www.architecture-weekly.com/p/architecture-weekly-189-mastering)

**Brief:** Instead of creating new connections each time we want to access the database, it maintains a "pool" of available connections. The number of connections in the pool is initially fixed. When a query is completed, the connection is sent back to the pool for reuse. 

A pool can be resized dynamically (e.g., when demand exceeds the pre-defined number or when demand is low).  
**Result:** Reduces latency of creating new connections and boosts performance.

*Considerations:* pool size, connection timeout

Connections are stored in local memory. It's a data structure in the RAM. It stores the state (is a transaction open?, where is the cursor?).  
With SQLite, the database is a file on disk, not a remote server that can be connected to.

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

### Threads
--------------

A thread is the smallest sequence of programmed instructions that a CPU can manage independently. The CPU switches between threads very quickly, so it looks like multiple are working at once, even though the CPU is just jumping from one thread to another (very quickly, some milliseconds).  
An app's "down time" is usually due to I/O operations, like waiting for a database response. In a single-threaded program, the entire program must wait for the execution to finish before continuing. In multi-threaded programs, another thread can work on something else while waiting for that database connection, for example.  

**Memory:** threads share the same memory space. They share the same pointers to addresses in memory. Therefore, they don't need to copy big data from registers for each operation, they have the addresses of the data already. This reduces RAM usage, threads don't need private copies of the entire program's data. Furthermore, threads can see the engine object in memory. When Thread A calls `session.add(job)`, the CPU is executing instructions in the context of Thread A, but it modifies bits at the memory address of that shared connection (engine) object.

**Downside:** when multiple threads are working, they may overlap and rewrite one-another's data, a ***race condition***. This leads to corruption if multiple threads want to write to the same byte in RAM at the same time.  
*Note:* threads are writing to the database from a single connection here.  

Pooling solves this by creating separate spaces in memory, the connection memory address isn't shared, many are made. Thread A can connect to the `Connection_01` address in memory, marking it now as "busy". Another working thread, Thread B, asks for a connection. The pool sees `Connection_01` is busy, so it gives it a new connection, `Connection_02`. They can now both write without corruption.

This made me think: how can this be parallel execution? Well operations that don't require writes are done in parallel, reading from the database is completely fine and done in parallel by multiple threads with specific instructions.

**Example:**    
Thread A can fetch data from an API, parse JSON and create some structure with it (CPU/Network intensive).  
Thread B can validate a password using the database, a read.  
> This is parallel, each thread has its own memory space to perform work from pooling, but share RAM (database settings, connection pool, metadata, etc.).  

However, parallelism is an illusion when it comes to `.commit()` in SQLite. Threads need to wait for the other to complete its write before doing its own write. This follows the **Isolation** principle.  
Postgres solves this by being a server with multiple processes. It doesn't directly write to a row in the database, it creates a new draft of the row. The original one is marked as "expired", but can still be read from other connections, allowing operations to continue.

**SQLITE:**
- `connect_args={"check_same_thread": False}`: non-default; SQLite prevents sharing a connection across multiple threads by default, i.e. when `True`. When only one thread is in use, a user may have to wait and sit in front of a loading screen, waiting for that thread to finish its execution (math, data processing, etc.). This tells SQLite that we *know* multiple threads may touch the database and that it's allowed.

