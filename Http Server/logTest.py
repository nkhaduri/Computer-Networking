import requests
from testsbase import testsbase
import time

class logTest(testsbase):
    def __init__(self, config):
        super().__init__(config)

    def run(self, vh=None):
        test_list = [
            self.test1,  # 200
            self.test2,  # 206
            self.test3,  # 304
            self.test4,  # 404
        ]
        return super().run(tests=test_list, vh=vh, testfile='index.html')

    def test1(self):
        """ check for 200 code log """
        response = requests.get(self.url)
        return self.check_log(response, 'logs/' + self.domain + '.log', self.domain)

    def test2(self):
        """ check for 206 code """
        response = requests.get(self.url, headers={"Range": "bytes=0-4"})
        return self.check_log(response, 'logs/' + self.domain + '.log', self.domain)

    def test3(self):
        """ check for 304 code """
        response = requests.get(self.url)
        etag = response.headers['etag']
        response = requests.get(self.url, headers={'If-None-Match': etag})
        return self.check_log(response, 'logs/' + self.domain + '.log', self.domain)

    def test4(self):
        """ checking for 404 error """
        headers = {'host': 'google.com'}
        response = requests.get(self.url, headers=headers)
        return self.check_log(response, 'logs/error.log', 'google.com')

    def check_log(self, r, log, d):
        try:
            f = open(log, 'rb')
            l = str(f.read(), 'utf-8').split('\n')[-2]
            # print(l)
            f.close()
            time.strptime(l[l.find('[') + 1:l.find(']')], "%a %b %d %H:%M:%S %Y")
            l = l[l.find(']') + 2:]
            ip, domain, path, code, size, _ = l.split()
            domain = domain.split(':')[0]
            return ip == self.ip and domain == d \
                   and path == '/index.html' and code == str(r.status_code) \
                   and size == r.headers['content-length']
        except Exception:
            return False
