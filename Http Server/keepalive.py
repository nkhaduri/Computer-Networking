import requests
from testsbase import testsbase

class keepalive(testsbase):
    def __init__(self, config):
        super().__init__(config)

    def run(self, vh=None):
        test_list = [self.test1, self.test2, self.test3]
        return super().run(tests=test_list, vh=vh, testfile='index.html')

    def test1(self):
        """ check keep-alive header """
        response = requests.get(self.url, headers={'Connection': 'keep-alive'})    
        return ('connection' in response.headers and 'keep-alive' in response.headers['connection'])

    def test2(self):
        """ check keep-alive header 2 """
        response = requests.get(self.url, headers={'Connection': 'keep-alive'}) 
        return ('keep-alive' in response.headers)

    def test3(self):
        """ get two requests """
        s = requests.Session()
        base_url = "http://" + self.domain + ':' + str(self.port) + '/'
        r1 = s.get(base_url + 'index.html')
        r2 = s.get(base_url+'ourwork.html')
        return ('keep-alive' in r2.headers and r1.status_code == 200 
                and r2.status_code == 200)

