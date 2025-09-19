"""Pingable class to compare ip address ping results on different subnets."""

import os
import sys
import logging
import asyncio
import ipaddress

logger = logging.getLogger(__name__)


class Pingable(ipaddress.IPv4Network):
    """Class for testing pings on subnets."""
    def __init__(self, address='192.168.0.0/24', require_24_cidr=False,
                 ip_ignore_list=None, strict=False, retries=1):
        """ Given a particular subnet, this class can ping each ip address
        within that subnet using the ping command.

        Inputs:
        address -- A string in the form of a CIDR subnet.
            For example, "192.168.1.0/24"
        require_slash_24 -- Requires a /24 CIDR.  Default allows any CIDR.
        ip_ignore_list -- A list of ints representing the last octet of ip.
            Matching ip adresses will be ignored.
        strict -- strict=False allows 192.168.1.1/24 as
            subnet dispite having a ".1" as last octet.  strict_subnets=True
            would instead require 192.168.1.0/24 as subnet where the last
            octet must be a ".0".
        retries -- The number of times each ping will be repeated.
        """
        super().__init__(address=address, strict=strict)
        self.require_24_cidr = require_24_cidr
        self.check_cidr()
        self.retries = retries
        self.pingable_ips = {}
        if ip_ignore_list is None:
            ip_ignore_list = []
        self.ip_ignore_list = ip_ignore_list # list of ints (last octet of ip)
        #self._semaphore = asyncio.Semaphore(100) # This does not appear to be needed
        # because asyncio appears to work on a limited number of tasks at a time.
        # https://stackoverflow.com/questions/48483348/how-to-limit-concurrency-with-python-asyncio
        # Above link could be used to limit tasks further.
        self.windows = os.name == 'nt'

    def check_cidr(self):
        """ Special check for CIDR of exactly /24. """
        if self.require_24_cidr:
            if str(self.netmask) != '255.255.255.0':
                msg = f'Given {self.exploded} has an invalid CIDR.  Only /24 CIDR is allowed.\n'
                msg += f'  Example: "192.168.1.0/24"'
                raise ipaddress.AddressValueError(msg)

    def ips(self, use_ignore_set=True, remove_found=True):
        """ Returns a list (comprehension) of all ip addresses in subnet as
            strings.
        """
        ips = [ip.exploded for ip in self.hosts()]
        if use_ignore_set:
            ip_ignore_set = set([octet for octet in self.ip_ignore_list if octet > 0 and octet < 255])
            ips = [ip for ip in ips if int(ip.split('.')[3]) not in ip_ignore_set]
        if remove_found:
            ip_found_list = [ip for ip, found in self.pingable_ips.items() if found]
            ips = [ip for ip in ips if ip not in ip_found_list]
        return ips

    async def ping_ip(self, ip):
        """ Ping given ip address using host OS.
            Command and result will be unique on different OS (Windows vs. Linux).
        """
        result = await asyncio.create_subprocess_shell(
            f'ping {"-n" if self.windows else "-c"} 1 {ip}',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stout, _ = await result.communicate()
        key = 'bytes=' if self.windows else 'rtt min/avg/max/mdev'
        self.pingable_ips[ip] = key in str(stout)
        logger.debug('%s %s', ip, 'Found' if self.pingable_ips[ip] else 'Missing')

    async def _ping_ips(self):
        """ Put all ping commands in separate asyncio tasks. """
        for _ in range(self.retries):
            tasks = [asyncio.create_task(self.ping_ip(ip)) for ip in self.ips()]
            await asyncio.wait(tasks)

    def ping_ips(self):
        """ Ping all ip addresses in subnet. """
        logger.info('Attempting to ping subnet %s', self.exploded)
        asyncio.run(self._ping_ips())
        logger.info('All ip addresses in subnet %s have been pinged', self.exploded)


def compare_subnets(subnet_1, subnet_2):
    """ Compare ping results of two subnets.

    Inputs:
    subnet_1 -- This can be a subnet in string format, or a Pingable object.
    subnet_2 -- The second subnet to compare with subnet_1.  See subnet_1.

    Returns a list of dictionary pairs where each pair has matching
        ending ip octets from different subnets, and ping results have
        different success value.  Note, this only works with hostmasks
        of 0.0.0.255 or subnets of that.
    """
    if isinstance(subnet_1, Pingable):
        p_1 = subnet_1
    else:
        p_1 = Pingable(subnet_1)
    p_1.ping_ips()
    pingable_1 = {key.split('.')[3]:val for key, val in p_1.pingable_ips.items()}
    network_1_front = str(p_1.network_address).rsplit('.', maxsplit=1)[0]

    if isinstance(subnet_2, Pingable):
        p_2 = subnet_2
    else:
        p_2 = Pingable(subnet_2)
    p_2.ping_ips()
    pingable_2 = {key.split('.')[3]:val for key, val in p_2.pingable_ips.items()}
    network_2_front = str(p_2.network_address).rsplit('.', maxsplit=1)[0]

    return [[{f'{network_1_front}.{key}':val},
             {f'{network_2_front}.{key}':pingable_2[key]}]
            for key, val in pingable_1.items()
            if key in pingable_2 and pingable_2[key] != val]

def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    arg_len = len(sys.argv)
    if arg_len == 3:
        subnet_1 = sys.argv[1]
        subnet_2 = sys.argv[2]
    else:
        print('Wrong number of arguments.')
        print("Let's assume you meant the following:")
        print('   $ compare_subnets 192.168.0.0/24 192.168.1.0/24')
        subnet_1 = '192.168.0.0/24'
        subnet_2 = '192.168.1.0/24'
    print(f'Pinging all hosts in {subnet_1} and {subnet_2}...')
    results = compare_subnets(subnet_1, subnet_2)
    for each in results:
        print(each)

def test_pingable():
    p = Pingable('192.168.0.0/28', require_24_cidr=True)

if __name__ == '__main__':
    test_pingable()

