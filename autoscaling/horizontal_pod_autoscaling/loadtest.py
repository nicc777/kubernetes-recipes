from locust import HttpUser, task

class TestService(HttpUser):
    @task
    def test(self):
        self.client.get("/example003")
        self.client.get("/example003/test")
