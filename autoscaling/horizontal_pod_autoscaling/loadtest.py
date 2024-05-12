from locust import HttpUser, task

class TestService(HttpUser):

    @task(weight=1)
    def test_root(self):
        self.client.get("/example003")

    @task(weight=3)
    def test_app(self):
        self.client.get("/example003/test")
