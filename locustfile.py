"""Load test for Compass's own server, not for Wikimedia.

    STRESS_TEST=1 COMPASS_RATE_LIMIT=0 python backend/app.py
    locust -f locustfile.py --host http://127.0.0.1:5000

With STRESS_TEST=1 the Guide endpoint returns canned data after 0.1 s instead of
calling Wikimedia, and every request uses a new random title so the guide cache never
answers: this measures Compass's threads and request handling.

Set LOCUST_COMPASS_USERS (comma-separated) to also load the dashboard endpoints for
those editors. Warm them first (`python backend/warm.py <names>`) so they're answered
from the caches; never load-test uncached users, since each miss fans out into dozens
of calls to Wikimedia's public APIs.
"""
import os
import random
import uuid

from locust import HttpUser, between, task

USERS = [u.strip() for u in os.environ.get('LOCUST_COMPASS_USERS', '').split(',') if u.strip()]


class GuideUser(HttpUser):
    wait_time = between(0, 0)  # as fast as possible

    @task
    def get_article_guide(self):
        self.client.get(f'/api/article/Topic_{uuid.uuid4()}/guide', name='/api/article/[title]/guide')


if USERS:
    class DashboardUser(HttpUser):
        wait_time = between(1, 3)

        @task(3)
        def profile(self):
            self.client.get(f'/api/profile/{random.choice(USERS)}', name='/api/profile/[user]')

        @task(3)
        def tasks(self):
            self.client.get(f'/api/tasks/{random.choice(USERS)}', name='/api/tasks/[user]')

        @task(2)
        def revisit(self):
            self.client.get(f'/api/revisit/{random.choice(USERS)}', name='/api/revisit/[user]')
