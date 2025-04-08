""" Costomizing the VISA Device for Hantek DSO2C10 Oscilloscope. """
import time
from andy.visa.cli import cli
from andy.visa.comms import Msg, Device


class DSO2000Msg(Msg):
    """ A message for the DSO2000 Series Digital Oscilloscope. """
    def __init__(self, cmd=''):
        """ Contains a creation time and ASCII command.

        Input:
            cmd (str): The command in the message can be specified during
                creation.
        """
        super().__init__(cmd)

    def __str__(self):
        """ Better printout """
        s = f'Created at: {self.creation_time}\n'
        if self.orig_cmd != self.cmd:
            s += f'CMD: {self.cmd} (Originally: {self.orig_cmd})\n'
        else:
            s += f'CMD: {self.cmd}\n'
        s += f'Sent at {self.send_time} with Timeout: {self.timeout}\n'
        s += f'Response was: {self.response} at time: {self.response_time}'
        return s

    def validate(self, cmd):
        """ Fix common cmd mistakes. Inject responses for obvious wrong
        cmd which are not worth sending.  When implementing your own
        validate method, it is best to copy the original method and modify.

        Inputs:
            cmd (str): The VISA command to validate.

        Note: Changing Msg.response will cause VISA_Device to not send
        command to instrument.

        Programmer notes:
        1) The DSO2000 manual states ":" is required before all commands, but
         this is not true.  Commands missing colon prefixed work.
        """
        cmd = str(cmd) # Make sure input is a string.
        if cmd == '':
            self.response = self.SYNTAX_ERR
        elif cmd[0] != ':':
            cmd = f':{cmd}'

        parts = cmd.split()
        front = parts[0].upper()
        try:
            back = f' {parts[1]}'
        except IndexError:
            back = ''
        cmd = f'{front}{back}'

        if cmd == ':WAV:DATA:ALL?':
            # This cmd works once, then times out after that.  I do not get it.
            # Temporary solution is to hid this cmd from Instrument and always
            # give fake response.
            self.response = '#900000012800000409900000000010-0020000000000004.9e-3204.9e-3184.9e-3184.9e-31810002.500e+04000001+0.00e+00+0.00e+00000893779'
            self.send_time = time.time()
            self.response_time = self.send_time

        return cmd


def proc_waveform_data(data):
    """ This processes commmand ':WAV:DATA:ALL?' """
    d = {}
    d['#9'] = data[0:2]
    d['packet byte length'] = data[2:11]
    d['amount of data'] = data[11:20]
    d['uploaded data length'] = data[20:29]
    d['running status'] = data[29]
    d['trigger status'] = data[30]
    d['ch1 offset'] = data[31:35]
    d['ch2 offset'] = data[35:39]
    d['ch3 offset'] = data[39:43]
    d['ch4 offset'] = data[43:47]
    d['ch1 voltage'] = data[47:54]
    d['ch2 voltage'] = data[55:61]
    d['ch3 voltage'] = data[61:68]
    d['ch4 voltage'] = data[68:75]
    d['ch enabled'] = data[75:79]
    d['sample rate'] = data[79:88]
    d['sampling multiple'] = data[88:94]
    d['trigger time'] = data[94:103]
    d['data aqu start time'] = data[103:112]
    d['reserved bits'] = data[112:128]
    return d

def main():
    """
    On Windows, it was discovered that installing Hantek software would
    change the USB driver to "USB Test Instrument..."  That makes the VISA
    Device fail to be found.  Uninstall that driver in Windows Device Manager.
    Then plug out and plug back in the usb port to the oscilloscope.  Now, the
    "DSO2C10" device should show up under "Universal Serial Bus devices".
    Once that shows the Command Line Interface should connect.

    On my Windows Surface Pro, the Hantek software never connected to the
    oscilloscope.  I gave up.
    """
    cli(DSO2000Msg)

def test():
    """ Used during development--ongoing. """
    msg = DSO2000Msg(':WAV:DATA:ALL?')
    msg = DSO2000Msg('WAV:DATA:ALL?')
    #msg = DSO2000Msg('chan1:scal 20mV')
    msg.timeout = 3000
    #dev = Device()
    #dev.send(msg)
    print(msg)
    #output = '#900000012800000409900000000010-0020000000000004.9e-3204.9e-3184.9e-3184.9e-31810002.500e+04000001+0.00e+00+0.00e+00000893779'
    #data = proc_waveform_data(output)
    #for key, val in data.items():
    #    print(f'{key}: {val}')

if __name__ == '__main__':
    test()
