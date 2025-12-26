""" Message Server and Client """
import sys
import asyncio
import logging

log = logging.getLogger(__name__)

class Server:
    """ Simple message server that connects clients. """
    def __init__(self, host='127.0.0.1', port=1025):
        """ Give a host and port or use defaults for testing. """
        self.host = host
        self.port = port
        self.message_queue = {}

    async def serve(self):
        """ Start server for listening and sending. """
        server = await asyncio.start_server(self.proc_client, self.host, self.port)
        async with server:
            try:
                await server.serve_forever()
            except Exception as e:
                print('what the hell:', e)
        log.warning('Server has shut down.')

    async def proc_client(self, reader, writer):
        """ Process a single client who has connected to server. """
        log.debug('Got request to serve client.')
        address = writer.get_extra_info('peername')
        data = await reader.readline() # Expect client to immediately send their name.
        client = data.decode()[:-1]
        log.info('%s connected from %s.', client, address)
        if client not in self.message_queue.keys(): # All clients must have a message queue.
            self.message_queue[client] = asyncio.Queue()

        write_task = asyncio.create_task(self._write(writer, client))
        await self._read(reader, client)
        write_task.cancel()
        log.info('%s is no longer connected from %s.', client, address)

    async def _read(self, reader, name):
        """ Read from stream reader for particular client. """
        while True:
            log.debug('read loop for %s.', name)
            try:
                data = await reader.readline()
                log.debug('Got something from %s: %s', name, data.decode())
            except asyncio.CancelledError: # is this a real error?
                log.debug('ConnectionResetError detected with user %s.', name)
                break
            except Exception as e:
                log.debug('not sure, but error for %s: %s', name, e)
                break
            if data:
                msg = data.decode()
                target_user, message = msg.split(':', 1) # All messages are "user:message" format.
                log.debug('%s sending message "%s" to %s.', name, message, target_user)
                if target_user not in self.message_queue.keys():
                    self.message_queue[target_user] = asyncio.Queue()
                try:
                    await self.message_queue[target_user].put(f'{name}:{message}')
                except KeyError:
                    emsg = 'User %s does not have message queue. Cannot send message'
                    log.warning(emsg, target_user)
            else:
                log.debug('Reading no data, so stopping.')
                # Notice on Linux machine, that reader.read() returns nothing when connection is
                #  cut on client side.  That will cause an endless loop in this task, so breaking
                #  that here.  I suppose returning nothing always, is better than waiting always.
                #  How else can the reader tell us that there is no connection during
                #  await reader.readline()?
                break
        log.debug('Reading shutdown for %s.', name)

    async def _write(self, writer, name):
        """ Write to stream writer for particular client. """
        while True:
            log.debug('write loop for %s.', name)
            try:
                msg = await self.message_queue[name].get()
                log.debug('message_queue for %s has raw message, "%s"', name, msg)
            except KeyError:
                log.warning('User %s does not have a queue.', name)
                break
            except Exception as e:
                log.warning('Some unknown error for %s\'s queue: %s', name, e)
                break
            try:
                writer.write(msg.encode())
                await writer.drain()
            except Exception as e:
                log.warning('Strange writer error with user %s: %s', name, e)
                break
        log.debug('Done writing for %s.', name)

    def current_clients(self):
        """ Will check and verify in future. """
        return sorted(self.message_queue.keys())

    def remove_client(self, name): # Not sure what this really does anymore.  Needs updating.
        """ Removes a client and her messages from message_queue dictionary. """
        try:
            del self.message_queue[name]
        except KeyError:
            log.warning('%s was not available to delete in message_queue dictionary.', name)
        log.info('Client %s was deactivated.', name)


class Client:
    """ Clients connect to server, then send and receive anytime. """
    def __init__(self, name='noone', host='127.0.0.1', port=1025):
        """ Inputs:
            name (str): is case sensitive.
            host (str): default host is localhost.
            port (int) can be anything, but remember less than 1025 will require
                root permission.

            Note, test on localhost first before complicating with firewalls and
            external networking issues.
        """
        self.name = name
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None

    async def connect(self):
        """ Establish connection with server. """
        log.debug('Client %s loop begin.', self.name)
        reader, writer = await asyncio.open_connection(self.host, self.port)
        msg = f'{self.name}\n'
        writer.write(msg.encode()) # Once connected, must immediately send client name.
        await writer.drain()
        log.info('%s connected to server at %s:%s', self.name, self.host, self.port)
        self._reader = reader
        self._writer = writer

    async def send(self, user, message):
        """ Send message to user. """
        msg = f'{user}:{message}\n'
        try:
            self._writer.write(msg.encode())
            await self._writer.drain()
        except Exception as e:
            log.warning('No error expected for %s. %s', self.name, e)
            return False
        log.debug('%s sent message, "%s" to %s.', self.name, message, user)
        return True

    async def receive(self):
        """ Reads a single message from server and returns it.
            Return None whenever server sends empty bytes or some connection
            issue."""
        try:
            data = await self._reader.readline()
            log.debug('Data read for %s.', self.name)
        except asyncio.CancelledError:
            log.debug('connectionResetError for %s', self.name)
            return None
        except Exception as e:
            log.debug('Got strange exception for %s: %s', self.name, e)
            return None
        if data:
            msg = data.decode()
            return msg[:-1]
        log.debug('Read no data.')
        return None


class CLI(Client):
    """ Simple user interface to demonstrate sub-classing Client. """
    def __init__(self, user, friend, host='127.0.0.1', port=1025):
        """ CLI class must know about friend.
            Other parameters are passed to Client class."""
        super().__init__(user, host, port)
        self.friend = friend

    async def get_messages(self):
        """ Loop to receive messages. """
        while True:
            log.debug('Start client message loop for %s.', self.name)
            msg = await self.receive()
            log.debug('Got msg for %s.', self.name)
            if msg is None:
                return
            user, message = msg.split(':', 1)
            print(f'\n{user}>>{message}\n{self.name}>>', end='')

    async def run(self):
        """ This method starts the CLI (Command Line Interface) loop. """
        await self.connect()
        read_task = asyncio.create_task(self.get_messages())
        while True:
            message = await asyncio.to_thread(input, f'{self.name}>>')
            if len(message) < 1:
                continue
            if not await self.send(self.friend, message):
                print('Issue with server.')
                break
            if message[:7].lower() == 'goodbye':
                print('You have left the conversation.')
                break
        read_task.cancel()
        log.debug('cli halted.')


async def single_message(user, friend, message, host='127.0.0.1', port=1025):
    """ Log in, send message, then log out. """
    c = Client(user, host, port)
    await c.connect()
    await c.send(friend, message)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) == 4:
        log.debug('Sending single message.')
        asyncio.run(single_message(*sys.argv[1:]))
    elif len(sys.argv) == 3:
        log.debug('Starting cli.')
        cli = CLI(*sys.argv[1:])
        asyncio.run(cli.run())
    else:
        log.debug('Starting server.')
        s = Server()
        try:
            asyncio.run(s.serve())
        except KeyboardInterrupt:
            log.info('Keyboard has stopped the server.')
