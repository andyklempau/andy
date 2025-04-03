""" Communicating with any VISA instrument. """
import warnings
import time
import sys
import os
import pyvisa


class Msg():
    """ A generic VISA message. """
    COM_ERR = 'comm error'
    PROCESSING = 'processing'
    TIMEOUT = 'timeout'
    SYNTAX_ERR = 'syntax error'
    OK = 'success'

    def __init__(self, cmd=''):
        """ Contains a creation time and ASCII command.

        Input:
            cmd (str): The command in the message can be specified during
                creation.
        """
        self.creation_time = time.time()
        self.send_time = None
        self.response_time = None
        self.timeout = None # Wait duration in ms
        self.response = self.PROCESSING
        self.orig_cmd = cmd # Before validation
        self.cmd = self.validate(cmd)

    def __str__(self):
        """ What this class looks like when printed as a string. """
        s = f'{self.creation_time}'
        return f'{self.creation_time}_{self.cmd}'

    def validate(self, cmd):
        """ Fix common cmd mistakes.  Inject responses for obvious wrong
        cmd which are not worth sending.  When implementing your own
        validate method, it is best to copy the original method and modify.

        Inputs:
            cmd (str): The VISA command to validate.

        Note: Changing Msg.response will cause Device to not send
        command to instrument.
        """
        cmd = str(cmd) # Make sure input is a string.
        if cmd == '':
            self.response = self.SYNTAX_ERR
        return cmd


class Device():
    """ Class for talking with any VISA device.
    Specific issues addressed:
    1) Do not wait forever (hang) for instrument to respond.
    2) When single instrument is connected, use that one by default.
    Install requires the pyvisa and pyvisa-py packages.
    Use Python >= 3.11  Why?
    """
    TIMEOUT_MS = 10000
    TIMEOUT_ERR = 'Timeout error'

    def __init__(self, name=''):
        """ Minimal setup with object is created.

        Inputs:
            name (str): You may specify the resource name to use when
                multiple devices are connected.  See "name" property.
        """
        self.end_char_len = 1 # Linux might append 1 char.  TODO: verify
        if os.name == 'nt': # A Windows machine
            self.end_char_len = 2 # Windows is observed to append 2 chars.
        self._rm = pyvisa.ResourceManager('@py') # Use Python as VISA backend
        self._device_name = name
        self._device = self._get_device(self._device_name)

    @property
    def name(self):
        """ Return the name of the resource as a string--the named USB
        connection.
        This output can be used as input when creating an instance of
        VISA_Device object to specify particular device with this name.  This
        is useful when multiple VISA devices are connected to computer.
        """
        if self._device is not None:
            return self._device.resource_name
        return self._device_name
    
    @name.setter
    def name(self, name):
        """ Change name of device to use.
        The resource will be reset every time you rename.
        Note that name fractions can also work.  For example, "CN2443029079664"
        will use device containing that part number.
        """
        self.reset_device()
        self._device_name = name

    def list_devices(self):
        """ List available VISA devices.
        Note: Connected devices will not appear in list.  You may want to
        device.reset_device() to see it listed.
        """
        with warnings.catch_warnings(action='ignore'):
            return self._rm.list_resources()

    def reset_device(self):
        """ Force device reset. """
        self._device = None

    def _get_device(self, pn=None):
        """ Return the VISA resource or None if not found.
        
        Inputs:
          pn (string): Part Number used to select device in device list.
            First device (which usually works) will be selected when pn is
            not specifyed or is duplicated in device list.
            
        Note: Users should use device property to obtain resource--not this
        method; therefore, this method has been marked private.
        """
        devices = self.list_devices()
        if pn is not None:
            devices = [d for d in devices if pn in d]
        if len(devices) == 0:
            return None
        device = self._rm.open_resource(devices[0])
        device.timeout = self.TIMEOUT_MS
        return device

    @property
    def device(self):
        """ Return current open device, opens device and returns it,
        or returns None.
        """
        if self._device is not None:
            return self._device
        self._device = self._get_device(self._device_name)
        return self._device

    def _write(self, msg):
        """ Process write; store results in msg. """
        msg.send_time = time.time()
        try:
            result = self.device.write(msg.cmd)
        except ValueError:
            msg.response_time = time.time()
            msg.response = msg.COM_ERR
            self.reset_device()
            return
        except pyvisa.errors.VisaIOError:
            msg.response_time = time.time()
            msg.response = msg.TIMEOUT
            self.reset_device()
            return
        msg.response_time = time.time()
        if result - self.end_char_len == len(msg.cmd):
            # This is not verification that the instrument recieved message.
            # It only means the message was sent, or does it?
            msg.response = msg.OK
        else:
            # Maybe 2 chars at end of ASCII string.
            msg.response = f'{msg.COM_ERR}: {len(msg.cmd)} != {result}!'

    def _query(self, msg):
        """ Process query; store results in msg. """
        msg.send_time = time.time()
        try:
            msg.response = self.device.query(msg.cmd)
        except ValueError:
            msg.response = msg.COM_ERR
            self.reset_device()
        except pyvisa.errors.VisaIOError:
            msg.response = msg.TIMEOUT
            self.reset_device()
        msg.response_time = time.time()

    def send(self, cmd, cls=Msg):
        """ Send a command to the VISA instrument.

        Inputs:
            cmd (str or Msg): Can be an ASCII string.  For example:
                ":CHAN1:SCAL?"
                Alternately, can be a Msg object.  Msg objects have the
                advantage of specifying a timeout when command is expected
                to take a long time, and can have custom validation.
            cls (Msg class): This is a class--not an object!  Used to wrap cmd
                when cmd is a string.  When cmd is a Msg object, this parameter
                is ignored.

        Returns a Msg object.  See Msg object below.
            Use msg.response to see status/response of command.
        """
        if isinstance(cmd, str):
            msg = cls(cmd)
        else:
            msg = cmd

        if msg.response != msg.PROCESSING:
            return msg
        elif self.device is None:
            msg.response = msg.COM_ERR
            return msg

        if msg.timeout is not None:
            orig_timeout = self.device.timeout
            self.device.timeout = msg.timeout

        # Lets implement the ? command!  Here?
        if cmd[-1] != '?':
            self._write(msg)
        else:
            self._query(msg)

        if msg.timeout is not None:
            self.device.timeout = orig_timeout

        return msg


def main():
    """ Test with USB connection to Hantek DSO2C10 oscilloscope. """
    vdev = Device('USB0::1183::20574::CN2443029079664::0::INSTR')
    msg = vdev.send(':CHAN1:SCAL 5mV')
    print(msg.response)
    msg = vdev.send(':WAV:DATA:ALL?')
    print(msg.response)
    print(vdev.device.read())

if __name__ == '__main__':
    main()
