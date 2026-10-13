# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
import os
from celery import Celery
import graph as agents
celery = Celery("w", broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))
@celery.task(name="run_agents")
def run_agents(query, vision, profile): return agents.run(query, vision, profile)
