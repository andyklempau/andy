import sys
from andy.visa.comms import Device, Msg

def user_selects_device(visa_instrument):
    """ UI for selecting device among multiple options. """
    visa_instrument.reset_device()
    devices = visa_instrument.list_devices()
    if devices_len := len(devices) < 1:
        print('No devices are present; check connections, ensure power is on.')
        sys.exit(0)
    if devices_len > 1:
        print('Multiple devices found.  Please select one.')
        for n, each in enumerate(devices, 1):
            print(f' {n}) each')
        user_entry = input('Select number: ')
        try:
            user_entry = int(user_entry)
        except ValueError:
            print(f'You entered an invalid number: {user_entry}')
            sys.exit(0)
        index = user_entry - 1
        visa_instrument.device_part_number = devices[index]
        visa_instrument.reset_device()
    print(f'Using --> {visa_instrument.device}')

def process_user_cmd(visa_instrument, cls=Msg):
    """ UI for command entry. """
    cmd = input('Enter ASCII command: ')
    cmd_lower = cmd.lower()
    if cmd_lower == 'exit':
        sys.exit(0)
    elif cmd_lower == 'device':
        print(visa_instrument.device)
    else:
        msg = visa_instrument.send(cmd, cls)
        print(f'Sent --> {msg.cmd}')
        if msg.response == msg.OK:
            print('Response --> N/A')
        else:
            print(f'Response --> {msg.response}')

def _cli(cls):
    """ UI helper

    Inputs:
        cls (Message class): The message class--not object to use.
    """
    visa_instrument = Device()
    user_selects_device(visa_instrument)
    while True:
        process_user_cmd(visa_instrument, cls)

def cli(cls=Msg):
    """ UI logic

    Inputs:
        cls (Message class): The message class--not object to use.
    """
    try:
        _cli(cls)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    cli()
