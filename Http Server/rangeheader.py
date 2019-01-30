import requests
from testsbase import testsbase

class rangeheader(testsbase):
    """
    Range header tests
    """
    def __init__(self, config):
        super().__init__(config)

    def run(self, vh=None):
        test_list = [self.test1, self.test2, self.test3, self.test4]
        return super().run(tests=test_list, vh=None, testfile='images/home_1.jpg')

    def check_range(self, offset=0, length=-1):
        if length > 0:
            range_bytes = "bytes={}-{}".format(offset, offset+length-1)
        else:
            range_bytes = "bytes={}-".format(offset)

        response = requests.get(self.url, headers={"Range": range_bytes})
        return self.check_byhash(response, offset=offset, length=length)

    def test1(self):
        """ check ACCEPT-RANGES header """
        response = requests.head(self.url)
        return 'ACCEPT-RANGES' in response.headers

    def test2(self):
        """ check ACCEPT-RANGES header's value """
        response = requests.head(self.url)
        return response.headers['ACCEPT-RANGES'].lower() == 'bytes'

    def test3(self):
        """ check range 1000-1999 """
        return self.check_range(offset=1000, length=1000)

    def test4(self):
        """ check range 0- """
        return self.check_range(offset=1000, length=-1)


    def test5(self):
        """ check for overlap """
        # In case of a range request that is out of bounds (range values overlap the extent of the resource), 
        # the server responds with a 416 Requested Range Not Satisfiable status.
         
        range_bytes = "bytes={}-{}".format(555, 111)
        response = requests.get(self.url, headers={"Range": range_bytes})
        return response.status_code == 416