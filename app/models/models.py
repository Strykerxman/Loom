from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base

class JobTable(Base):
    __tablename__ = 'jobs'

    job_id = Column(Integer, primary_key=True, index=True) # Stores the ID of a given Job, primary key and indexed for quick lookups
    status = Column(String, default="pending", nullable=False) # Stores status of a given Job, indexed for quick lookups (eg. pending, running, done, failed)
    created_at = Column(DateTime) # Stores time at which a Job was created, may be indexed later on, but not critical

    tasks = relationship("TaskTable", back_populates='job')

    # A Job is a general goal, while a Task is an execution that is part of a Job.
    # We separate them so that if an error occurs during a Job, we identify the specific Task that failed w/o having to start all over
    # If Task #50 failed out of 100, we try it again say 3 times and move along if it did not succeed.
    # Of course, it's important to check which Task failed and how critical it is for a Job.

class TaskTable(Base):
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True, index=True) # Stores the ID of a given Task
    parent_job_id = Column(Integer, ForeignKey('jobs.job_id')) # Stores the ID of the Job that contains this Task
    payload = Column(JSONB) 
    response = Column(JSONB)

    evaluation_result = Column(JSONB)

    error_log = Column(String)
    retry_count = Column(Integer, default=0, nullable=False)
    status = Column(String, default="pending", nullable=False)

    job = relationship("JobTable", back_populates='tasks')