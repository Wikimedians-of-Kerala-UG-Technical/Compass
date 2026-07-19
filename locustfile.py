from locust import HttpUser, task, between
import uuid
import random

class WikiAPIUser(HttpUser):
    # ZERO wait time to absolutely hammer the server and maximize CPU/Thread usage
    wait_time = between(0, 0)

    @task(1)
    def get_article_guide(self):
        # We append a random UUID to the title to explicitly BYPASS the @lru_cache.
        # If we didn't do this, the cache would return the result in 0.0001s 
        # and you wouldn't see the actual thread limitations.
        random_title = f"Topic_{uuid.uuid4()}"
        self.client.get(f"/api/article/{random_title}/guide", name="/api/article/[title]/guide")

    @task(3)
    def get_article_references(self):
        # This endpoint spawns 5 threads internally. 
        # Hammering this will quickly exhaust the ThreadPoolExecutor or Gunicorn workers.
        random_title = f"Topic_{uuid.uuid4()}"
        offset = random.choice([0, 5, 10])
        self.client.get(f"/api/article/{random_title}/references?offset={offset}", name="/api/article/[title]/references")
