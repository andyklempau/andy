"""Pingable class to compare ip address ping results on different subnets."""

import os
import sys
import logging
import asyncio
import ipaddress

logger = logging.getLogger(__name__)


class IPv4Net(ipaddress.IPv4Network):
    """ Specialized IPv4Network with CIDR restriction. """
    def __init__(self, address='192.168.0.0/24', strict=False, require_24_cidr=False):
        """
        Inputs:
        address -- A string in the form of a CIDR subnet.
            For example, "192.168.1.0/24"
        require_slash_24 -- Requires a /24 CIDR.  Default allows any CIDR.
        strict -- strict=False allows 192.168.1.1/24 as
            subnet dispite having a ".1" as last octet.  strict=True
            would instead require 192.168.1.0/24 as subnet where the last
            octet must be a ".0".
        """
        super().__init__(address=address, strict=strict)
        self.require_24_cidr = require_24_cidr
        self.check_cidr()

    def check_cidr(self):
        """ Special check for CIDR of exactly /24. """
        if self.require_24_cidr:
            if str(self.netmask) != '255.255.255.0':
                msg = f'Given network-->{self} has an invalid CIDR.  Only /24 CIDR is allowed.\n'
                msg += '  Example: "192.168.1.0/24"'
                raise ipaddress.AddressValueError(msg)


class Pingable():
    """Class for testing pings on subnets."""
    def __init__(self, network=None, ip_ignore_list=None, retries=1):
        """ This class can ping each host within a particular network using
        the ping command.

        Inputs:
        network -- An IPv4Net type
        ip_ignore_list -- A list of ints representing the last octet of ip.
            Matching ip adresses will be ignored.
        retries -- The number of times each ping will be repeated if not found.
        """
        if network is None:
            network = IPv4Net()
        self.network = network
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

    def ips(self, use_ignore_set=True, remove_found=True):
        """ Returns a list (comprehension) of all ip addresses in subnet as
            strings.
        """
        ips = [ip.exploded for ip in self.network.hosts()]
        if use_ignore_set:
            ip_ignore_set = {octet for octet in self.ip_ignore_list if 0 < octet < 255}
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
        logger.info('Attempting to ping subnet %s', self.network)
        asyncio.run(self._ping_ips())
        logger.info('All ip addresses in subnet %s have been pinged', self.network)


def compare_subnets(ping_1, ping_2):
    """ Compare ping results of all hosts in two networks.

    Inputs:
    ping_1 -- A Pingable object containing a network to ping.
    ping_2 -- The second Pingalbe object to compare with ping_1's network.

    Returns a list of dictionary pairs where each pair has matching
        ending ip octets from different networks, and ping results have
        different success value.  Note, this only works with hostmasks
        of 0.0.0.255 or subnets there of.
    """
    ping_1.ping_ips()
    pingable_1 = {key.split('.')[3]:val for key, val in ping_1.pingable_ips.items()}
    network_1_front = str(ping_1.network).rsplit('.', maxsplit=1)[0]

    ping_2.ping_ips()
    pingable_2 = {key.split('.')[3]:val for key, val in ping_2.pingable_ips.items()}
    network_2_front = str(ping_2.network).rsplit('.', maxsplit=1)[0]

    return [[{f'{network_1_front}.{key}':val},
             {f'{network_2_front}.{key}':pingable_2[key]}]
            for key, val in pingable_1.items()
            if key in pingable_2 and pingable_2[key] != val]

def main():
    """ Handle CLI """
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
    net_1 = IPv4Net(subnet_1)
    net_2 = IPv4Net(subnet_2)
    print(f'Pinging all hosts in {net_1} and {net_2}...')
    results = compare_subnets(Pingable(net_1), Pingable(net_2))
    for each in results:
        print(each)

if __name__ == '__main__':
    main()
