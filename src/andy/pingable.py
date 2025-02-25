"""Pingable class to compare ip address ping results on different subnets."""

import logging
import asyncio
import ipaddress

logger = logging.getLogger(__name__)


class Pingable():
    """Class for testing pings on subnets."""
    def __init__(self, subnet='192.168.0.0/24', require_24_cidr=False):
        self._retries  = 1
        self._ip_ignore_list = [] # list of ints (last octet of ip)
        self.require_24_cidr = require_24_cidr
        self._subnet = None
        self.subnet = subnet # calls setter
        self.pingable_ips = {} # altered by ping_ip method

    @property
    def retries(self):
        """ The number of times to ping a single ip address. """
        return self._retries

    @retries.setter
    def retries(self, number=1):
        """ Setter for retries is limited to 1, 2, or 3.
            Warning logged if attempt to set outside of allowable range.
        """
        if number not in (1, 2, 3):
            msg = 'Input "retries" must be 1, 2, or 3 only. "%s" is invalid.'
            msg += '  Defaulting to 1.'
            logger.warning(msg, number)
        self._retries = number

    @property
    def ip_ignore_list(self):
        """ A list of integers representing the last octet of ip address.
            IPs ending with these octets will not be pinged.
            Each IP octet must be between 1-254 inclusive.
            Ints outside this range are removed after a warning is logged.
        """
        for ind, num in reversed(list(enumerate(self._ip_ignore_list))):
            if num < 0:
                msg = 'Number in ip_ignore_list is too small.'
                msg += '  "%s" will be removed.'
                logger.warning(msg, num)
                self._ip_ignore_list.pop(ind)
            elif num > 255:
                msg = 'Number in ip_ignore_list is too large.'
                msg += '  "%s" will be removed.'
                logger.warning(msg, num)
                self._ip_ignore_list.pop(ind)
        return self._ip_ignore_list

    @ip_ignore_list.setter
    def ip_ignore_list(self, ignore_list):
        """ ip_ignore_list must be list type.
            Note, due to user's ability to use .append on this list, only
                reading list will activate filter.
        """
        if isinstance(ignore_list, (list, tuple)):
            self._ip_ignore_list = list(ignore_list)
        else:
            msg = 'ip_ignore_list must be a list type; not %s.'
            logger.warning(msg, type(ignore_list))

    @property
    def subnet(self):
        """ Returns subnet; default is 192.168.0.0/24 """
        return self._subnet

    @subnet.setter
    def subnet(self, value):
        """ subnet setter
        Assignment can fail if given subnet is invalid.
        """
        if self.check_subnet(value, self.require_24_cidr):
            self._subnet = value

    @staticmethod
    def check_subnet(subnet, require_slash_24=False):
        """ Validates a subnet.

        Inputs:
        subnet -- A string in the form of a CIDR subnet.
            For example, "192.168.1.0/24"
        require_slash_24 -- Requires a /24 CIDR.  Default allows any CIDR.

        Returns True when subnet is valid, False when subnet is not valid.
        Note 1: strict=False allows 192.168.1.1/24 as subnet.  strict=True
            would instead require 192.168.1.0/24 as subnet.
        """
        if not isinstance(subnet, str):
            msg = 'Subnet input must be a string.  %s (type==%s) is invalid.'
            logger.error(msg, subnet, type(subnet))
            return False

        try:
            ip_net = ipaddress.IPv4Network(subnet, strict=False)  # see Note 1
        except (ipaddress.AddressValueError,
                ipaddress.NetmaskValueError) as err:
            logger.error('Invalid subnet "%s"--> %s', subnet, err)
            return False

        if require_slash_24:
            if str(ip_net.netmask) != '255.255.255.0':
                msg = '%s is an invalid CIDR.  Only /24 CIDR is allowed.'
                msg += '  Example: "192.168.1.0/24"'
                logger.error(msg, subnet)
                return False

        return True

    @property
    def subnet_base(self):
        """ The subnet without the last octet or prefix length. """
        try:
            return self.subnet[0:self.subnet.rfind('.') + 1]
        except (AttributeError, IndexError):
            return None

    @property
    def ips(self):
        """ Returns a list (comprehension) of all ip addresses in subnet as
            strings.
        """
        try:
            ip_net = ipaddress.IPv4Network(self.subnet, strict=False)
        except ipaddress.AddressValueError:
            logger.error('Invalid subnet likely.')
            return []
        all_ips = [ip.exploded for ip in ip_net.hosts()]
        ips_of_interest = [ip for ip in all_ips
                           if int(ip.split('.')[3]) not in self.ip_ignore_list]
        return ips_of_interest

    def ping_ips(self):
        """User facing method to ping all ips for prespecified subnet."""
        try:
            asyncio.run(self._ping_ips())
        except ValueError:
            logger.error('Error with ping_ips.')

    async def _ping_ips(self):
        """Helper method for ping_ips."""
        tasks = [asyncio.create_task(self.ping_ip(ip)) for ip in self.ips]
        await asyncio.wait(tasks)

    async def _ping_ip(self, ip):
        """Helper method for ping_ip."""
        result = await asyncio.create_subprocess_shell(
            f'ping -n {self.retries} {ip}',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await result.communicate()
        found = str(out).find('bytes=') # Successful pings contain "bytes=".
        return found >= 0

    async def ping_ip(self, ip):
        """ Ping given ip address.
        Nothing is returned, but pingable_ips dictionary is manipulated.
        """
        logger.debug('Pinging %s...', ip)
        found = await self._ping_ip(ip)
        self.pingable_ips[ip] = found # atomic assignment
        logger.debug('Finished pinging %s.', ip)


def compare_dicts(dict_1, dict_2):
    """ Find common keys between two given dictionaries whos values are
    different.

    Inputs:
    dict_1 -- First dictionary
    dict_2 -- Second dictionary

    Return a new dictionary containing the common keys and the values of
        each dictionary whos values are not equal.  For example:
            return {shared_key:[val_1, val_2]}
    """

    # Iterating on shortest dictionary is most efficient.
    if len(dict_1) < len(dict_2):
        short_dict = dict_1
        long_dict = dict_2
    else:
        short_dict = dict_2
        long_dict = dict_1

    differences = {}
    for key, val_1 in short_dict.items():
        try:
            val_2 = long_dict[key]
        except KeyError:
            continue
        if val_1 != val_2:
            differences[key] = [dict_1[key], dict_2[key]]

    return differences

def compare_subnets(subnet_1, subnet_2, retries=None, ignore_list=None):
    """Compares two subnets by pinging all ips in each and comparing results.

    Inputs:
    subnet1 -- The first subnet as string.  Recommend /24 CIDR only.  Note,
        192.168.1.1/24 is an allowed subnet although not strictly
        a proper format.
    subnet2 -- The other subnet as string.  Recommend /24 CIDR only.
    retries -- The number of ping attempts per ip address. Must be
        integer of either 1, 2, or 3.  Can be a list of two retries for
        each subnet, respectively.
    ignore_list -- A list of integers representing ending octets to ignore.
        Integers must be 1 - 254.

    Returns a list of dictionary pairs where each pair has matching
        ending ip octets as keys but have different boolean ping success
        results as values.
    """
    if retries is None:
        retries = [1, 1]
    elif isinstance(retries, int):
        retries = [retries, retries]
    if ignore_list is None:
        ignore_list = []

    pingable_1 = Pingable(subnet_1)
    pingable_1.retries = retries[0]
    pingable_1.ip_ignore_list = ignore_list
    pingable_1.ping_ips()
    subnet_base_1 = pingable_1.subnet_base
    octets_1 = {}
    for key, val in pingable_1.pingable_ips.items():
        octets_1[key.split('.')[3]] = val

    pingable_2 = Pingable(subnet_2)
    pingable_2.retries = retries[1]
    pingable_2.ip_ignore_list = ignore_list
    pingable_2.ping_ips()
    subnet_base_2 = pingable_2.subnet_base
    octets_2 = {}
    for key, val in pingable_2.pingable_ips.items():
        octets_2[key.split('.')[3]] = val

    results = []
    for octet, vals in compare_dicts(octets_1, octets_2).items():
        results.append([{f'{subnet_base_1}{octet}':vals[0]},
                        {f'{subnet_base_2}{octet}':vals[1]}])
    return results

def main():
    """ Command line call of compare_subnets """
    import sys
    arg_len = len(sys.argv)
    if arg_len == 3:
        subnet_1 = sys.argv[1]
        subnet_2 = sys.argv[2]
    else:
        print('Wrong number of arguments.')
        print('Example:')
        print('   $ compare_subnets 192.168.0.0/24 192.168.1.0/24')
        return
    results = compare_subnets(subnet_1, subnet_2, retries=[1, 3])
    for each in results:
        print(each)

if __name__ == '__main__':
    main()
