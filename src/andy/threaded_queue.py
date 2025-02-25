""" Demonstrate a threaded queue where add and remove actions could take a long
time, such as talking to a database. """
import threading
import time

class ThreadedQueue():
    """ Quick example of threaded queue. """
    def __init__(self):
        """ Create attributes and start action thread. """
        self.queue = []
        self.action_queue = []
        self.sleep_time = 0.01 # Time in seconds.
        action_thread = threading.Thread(target=self.action_thread, daemon=True)
        action_thread.start()

    def add(self, item):
        """ User facing add method. """
        self.action_queue.append(('add', item))

    def remove(self, index=0):
        """ User facing remove method. """
        self.action_queue.append(('remove', index))

    def get(self, number):
        """ User facing get which uses localy stored data. """
        try:
            return self.queue[number]
        except IndexError:
            return None

    def action_thread(self):
        """ The action thread where add and remove requests are initiated. """
        while True:
            try:
                action = self.action_queue.pop(0)
            except IndexError:
                time.sleep(self.sleep_time)
                continue

            if action[0] == 'remove':
                self._long_process_remove(action[1])
            else:
                self._long_process_add(action[1])

    def _long_process_add(self, item):
        """ A fictitious long processing add method. """
        time.sleep(1) # simulate a long process by sleeping for one second.
        self.queue.append(item)

    def _long_process_remove(self, index):
        """ A fictitious long processing remove method. """
        time.sleep(1) # simulate a long process by sleeping for one second.
        self.queue.pop(index)

def main():
    """ Show how queue changes over time. """
    tq = ThreadedQueue()
    tq.add('i do not care')
    tq.remove()
    tq.add('something new')
    tq.add(25)
    for i in range(20):
        print(i)
        print(' ', tq.get(0))
        print(' ', tq.get(1))
        time.sleep(0.3)

if __name__ == '__main__':
    main()
