import requests
from testsbase import testsbase
from numpy import mean

class virtualhost(testsbase):
    """
        Virtual hosting testing class
    """
    def __init__(self, config):
        super().__init__(config)

    def run(self):
        test_list = [self.test1, self.test2, self.test3]
    
        results = []
        for vh in self.config['server'][1:]:
            print("testing vs {}".format(vh))
            # r.append(super().run(vh))
            results.append(super().run(tests=test_list, vh=vh, testfile='index.html'))
        return mean(results)

    def test1(self):
        """ unknown domain """
        headers = {'host': 'google.com'}
        response = requests.get(self.url, headers=headers)
        return ((response.status_code == 404)
                 and ('REQUESTED DOMAIN NOT FOUND' in response.text.upper()))

    def test2(self):
        """ GET file, check sha254 """
        response = self.get
        return self.check_byhash(response)

    def test3(self):
        """ HOST header routing """
        return self.domain in self.get.text
