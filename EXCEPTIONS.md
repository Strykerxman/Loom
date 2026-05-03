### Exception Handling

```python
try:
    db_job = create_eval_job(db=db, prompts=prompts)
    return db_job
except HTTPException(status_code=500, detail="Database error"):
    return JobResponse(status="failed")
 ```

This is code that I had originally written in [evaluate.py](app/api/endpoints/evaluate.py)  
The issue is that this creates an `HTTPException` object and the `except` keyword expects an *Exception Class Type* (like ValueError, KeyError, or Exception), not an instantiated object. Python evaluates the `HTTPException(...)` first and checks if the thrown error matches the object. Python crashes with a `TypeError` as it expects a class type, not an instance.  

In FastAPI, it isn't intended to *return* an `HTTPException`, it should instead *raise* it. Raising makes FastAPI stop the execution of the function and it subsequently sends the HTTP response to the client.  

The above code should be replaced by:  
```python
try:
    # We try to do the dangerous database operation
    db_job = create_eval_job(db=db, prompts=prompts)
    return db_job

except Exception as e:
    # If ANYTHING goes wrong (database lock, memory error, etc.)
    # We catch the raw Python exception (e), and we RAISE a FastAPI exception.
    # This instantly sends a 500 status code back to the client.
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to create evaluation job: {str(e)}"
    )
 ```

Excepting any exception serves as a security measure. If `create_eval_job()` fails, it throws some raw SQLAlchemy errors. FastAPI will spew out a raw `500` error with no useful information, or worse, expose database stack traces to the client. Catching any exception allows the developer to control what the client sees.