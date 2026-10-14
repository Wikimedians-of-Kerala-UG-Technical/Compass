from locust import HttpUser, task, between
import uuid

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
