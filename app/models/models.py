from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base

class JobTable(Base):
    __tablename__ = 'jobs'

    job_id = Column(Integer, primary_key=True, index=True) # Stores the ID of a given Job, primary key and indexed for quick lookups
    status = Column(String, default="pending", nullable=False) # Stores status of a given Job
    created_at = Column(DateTime, server_default=func.now(), nullable=False) # Stores time at which a Job was created, may be indexed later on, but not critical

    tasks = relationship("TaskTable", back_populates='job', cascade="all, delete-orphan")

    # A Job is a general goal, while a Task is an execution that is part of a Job.
    # We separate them so that if an error occurs during a Job, we identify the specific Task that failed w/o having to start all over
    # If Task #50 failed out of 100, we try it again say 3 times and move along if it did not succeed.
    # Of course, it's important to check which Task failed and how critical it is for a Job.

class TaskTable(Base):
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True, index=True) # Stores the ID of a given Task
    parent_job_id = Column(Integer, ForeignKey('jobs.job_id', ondelete="CASCADE"), nullable=False, index=True) # Stores the ID of the Job that contains this Task
    payload = Column(JSONB, nullable=False) # {"prompt": prompt}, nullable=False because we need the prompt to process the task, and it should always be provided when we create a Task in the database
    response = Column(JSONB) # {"text": mock_response, "model": "mock-llm"}

    evaluation_result = Column(JSONB, nullable=True) # Stores the PII evaluation result as JSON, nullable because it won't be populated until after the worker processes the task

    error_log = Column(String)
    retry_count = Column(Integer, default=0, nullable=False)
    status = Column(String, default="pending", nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False) # should always exist
    updated_at = Column(DateTime, server_default=func.now(), nullable=False) # should always exist, no onupdate because its bound to SQLAlchemy
    started_at = Column(DateTime, nullable=True) # does not exist until claimed
    completed_at = Column(DateTime, nullable=True) # does not exist until terminal

    job = relationship("JobTable", back_populates='tasks')