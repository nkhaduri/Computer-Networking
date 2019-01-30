import json
from numpy import mean
from hashlib import sha256
import requests

class testsbase():
    """
    Range header tests
    """
    def __init__(self, config):
        with open(config, 'r') as f:
            self.config = json.load(f)

    def run(self, tests=None, vh=None, testfile='index.html'):
        if vh is None:
            vh = self.config['server'][0]

        self.domain = vh['vhost']
        self.ip = vh['ip']
        self.port = vh['port']
        self.docroot = vh['documentroot']
        self.url = "http://" + self.domain + ':' + str(self.port) + '/' + testfile
        self.testfile = self.docroot + '/' + testfile

        try:
            self.get = requests.get(self.url)
            self.head = requests.head(self.url) 
        except Exception as err:
            print("could not GET/HEAD file {} error: {}".format(self.url, err))
        score = []
        for t in tests:
            try:
                print("{0:12} {1:5} {2:40}: ".format(type(self).__name__, t.__name__, t.__doc__), end='')
                result = t()
                score.append(result)
                print(result)
            except Exception as err:
                print("test crashed: {}".format(err))

        return mean(score)

    def check_byhash(self, response, offset=0, length=-1):
        h = sha256()
        m = sha256()
        with open(self.testfile, "rb") as f:
            f.seek(offset, 0)
            data = f.read(length)
        
        h.update(data)
        m.update(response.content)

        return (m.digest() == h.digest())

