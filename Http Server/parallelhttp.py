import requests
from testsbase import testsbase
import threading
from queue import Queue
from time import sleep, time

class parallelhttp(testsbase):
    def __init__(self, config):
        super().__init__(config)
        self.q = Queue()

    def run(self, vh=None):
        test_list = [self.test1, self.test2]
        return super().run(tests=test_list, vh=vh, testfile='index.html')

    def worker(self):
        try:
            response = requests.get(self.url)
            self.q.put((response.status_code == 200) and (self.check_byhash(response)))
        except Exception as err:
            print(err)

    def parallel_clients(self, number_of_treads):
        threads = []
        for i in range(number_of_treads):
            t = threading.Thread(target=self.worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        results = [self.q.get() for _ in range(number_of_treads)]
        return all(results) and (len(results) == number_of_treads)
    
    def test1(self):
        """ 100 connections"""
        start = time()
        r = self.parallel_clients(100)
        return r and (time() - start < 1)

    def test2(self):
        """ 500 connections """
        start = time()
        r = self.parallel_clients(500)
        return r and (time() - start < 10)