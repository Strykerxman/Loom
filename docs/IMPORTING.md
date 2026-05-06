### Circular Imports

I originally had a circular import in my `models` directory. Let's trace it back.  
The `Base` class and the `engine`/`Session` are in the same file (`database.py`)  

- `models.py` needs `Base` to declare the shape of the data.
- `main.py` needs `engine` to boot up the database.
- `evaluate.py` needs `get_db` to get a session.  

These "needs" are all in **one** file, `database.py`  
I originally put those dependencies in the `__init__.py` in the **app/database** directory, i.e.

```python
from .database import get_db, init_db, Base
from .crud import create_eval_job
```

When running `uvicorn main:app`, it sees the API router, goes to the **app/api** directory, runs the `__init__.py` which has `endpoints.evaluate`, a file. Python reads it and sees `from app.database import create_eval_job`. Python goes to the **app/database** directory, runs its `__init__.py`, shown in the code above. The first line is okay, the second one (`from .crud import create_eval_job`) has Python open the `crud.py` file. It pauses its reading of the `app/database/__init__.py` file, i.e. it has not seen the `__all__` statement yet. In `crud.py` it sees `from app.models import JobTable`, it pauses its `crud.py` reading, goes to the **app/models** directory. Inside that directory, it runs the `__init__.py` file, sees `from .models import JobTable, TaskTable`, so it goes to `models.py`.  In `models.py`, we import `Base` from ***app/database/database.py***. But Python had paused it's reading of the `__init__.py` in the **app/database** directory.  
> This is the source of the crash.  

Because `app.database` is currently half-loaded, Python cannot pull `Base` from it.  
**Solution:** decouple `Base` from the `models.py` by putting it in its own file.  

1. The Empty Rule (Safest): Leave `__init__.py` files completely blank. Only use them to tell Python "this is a module." If something is needed, import it explicitly: `from app.database.crud import create_eval_job`. It's slightly more typing, but 100% bug-proof.
2. The "Leaf Node" Rule: When putting imports in an `__init__.py` to make a nice facade, the files inside that folder must be "leaf nodes." Meaning, `crud.py` and `database.py`, both in the **app/database** directory,  should not import from outside
their own folder at the top of the file.
3. The Architectural Rule: Separate the *data shape* (Base, models) from the *connection* (engine, Session). They should never live in the same folder hierarchy, because connections always need models, and models always need Base.
