# Demonstrate a threaded queue where add and remove actions could take a long
# time, such as talking to a database.
import threading
import time

class ThreadedQueue():
    def __init__(self):
        self.queue = []
        self.action_queue = []
        self.sleep_time = 0.01 # Time in seconds.
        action_thread = threading.Thread(target=self.action_thread, daemon=True)
        action_thread.start()

    def add(self, item):
        self.action_queue.append(('add', item))

    def remove(self, index=0):
        self.action_queue.append(('remove', index))

    def get(self, number):
        try:
            return self.queue[number]
        except IndexError:
            return None

    def action_thread(self):
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
        time.sleep(1) # simulate a long process by sleeping for one second.
        self.queue.append(item)

    def _long_process_remove(self, index):
        time.sleep(1) # simulate a long process by sleeping for one second.
        self.queue.pop(index)

def main():
    tq = ThreadedQueue()
    tq.add('i do not care')
    tq.remove()
    tq.add('something new')
    tq.add(25)
    for i in range(100):
        print(i)
        print(tq.get(0))
        print(tq.get(1))
        time.sleep(0.3)

if __name__ == '__main__':
    main()
