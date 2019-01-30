from testsbase import testsbase
import magic
import os
from numpy import mean

class basicHttp(testsbase):
    def __init__(self, config):
        super().__init__(config)

    def run(self, vh=None):
        test_list = [self.test2, self.test3, self.test4, self.test5, self.test7]
    
        docroot = self.config['server'][0]['documentroot']
        results = []
        for root, dirs, files in os.walk(docroot, topdown=False):
            for name in files:
                testfile = os.path.join(root, name)[len(docroot)+1:]
                print("test file: {}".format(testfile))
                results.append(super().run(tests=test_list, vh=vh, testfile=testfile))

        return mean(results)

    def test2(self):
        """ GET file, check sha254 """
        response = self.get
        return self.check_byhash(response)

    def test3(self):
        """ GET supported headers """
        response = self.get 
        headers = [h in response.headers for h in ['server', 
                    'date', 'content-length', 'content-type', 'etag']]   
        return all (headers)

    def test4(self):
        """ content-length """
        content_length = int(self.head.headers['content-length'])
        response = self.get
        return response.status_code == 200 and content_length == len(response.content)

    def test5(self):
        """ HEAD method """
        response = self.head        
        headers = [h in response.headers for h in ['server', 
                    'date', 'content-length', 'content-type', 'etag']]
        return len(response.text) == 0 and all(headers)

    # def test6(self):
    #     """ etag support """
    #     response = self.get
    #     etag = response.headers['etag']
    #     response = requests.get(self.url, headers={'If-None-Match': etag})
    #     return response.status_code == 304

    def test7(self):
        """ check mime-type """
        response = self.get
        return magic.from_buffer(response.content, mime=True) == response.headers['content-type']
