"""Test Pingable class."""
import unittest
import time
import asyncio
import logging
from andy.pingable import Pingable, compare_subnets, compare_dicts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class TestPingable(unittest.TestCase):
    """Tests Pingable class"""
    def test_subnet(self):
        """ Testing subnet and how large ip range can be. """
        p = Pingable('1.0.0.5/29')
        answer = ['1.0.0.1', '1.0.0.2', '1.0.0.3', '1.0.0.4', '1.0.0.5',
                  '1.0.0.6']
        self.assertEqual(p.ips, answer)

    def test_ip_ignore_list(self):
        """ Testing ip_ignore_list assignment and bad values. """
        p = Pingable()
        p.ip_ignore_list = (1, 2, 3)
        p.ip_ignore_list.append(-455)
        p.ip_ignore_list = 'what up'
        answer = [1, 2, 3]
        self.assertEqual(p.ip_ignore_list, answer)

    def test_compare_dicts(self):
        """ Testing compare_dicts """
        d_1 = {'1.0.0.1':True, '1.0.0.2':False, '1.0.0.3':True, '1.0.0.4':False, '1.0.0.5':True}
        d_2 = {'1.0.0.1':True, '1.0.0.2':False, '1.0.0.3':False, '1.0.0.4':True, '1.0.0.6':True}
        result = compare_dicts(d_1, d_2)
        answer = {'1.0.0.3': [True, False], '1.0.0.4': [False, True]}
        self.assertEqual(result, answer)

def test_compare_subnets():
    """ Testing compare_subnets """
    results = compare_subnets('192.168.0.0/28', '192.168.0.0/28',
                              retries=[1, 3])
    for each in results:
        print(each) # There is no consistancy here; some pings fail.

def test_ping_ip():
    """ Testing ping_ip one at a time. """
    p = Pingable()
    asyncio.run(p.ping_ip('192.168.0.1'))
    time.sleep(5)
    print(p.pingable_ips) # Answer will vary per local network.

if __name__ == '__main__':
    test_compare_subnets()
