from locust import HttpUser, task, between

class WikiAPIUser(HttpUser):
    # Wait between 1 and 3 seconds between requests per simulated user
    wait_time = between(1, 3)

    @task(1)
    def get_article_guide(self):
        # Testing the fast endpoint (Guide generation)
        self.client.get("/api/article/Python/guide")

    @task(3)
    def get_article_references(self):
        # Testing the heavy multiprocessing endpoint (Paginated references)
        # We give it a weight of 3 because users are more likely to click 'Load More'
        self.client.get("/api/article/Python/references?offset=0")
