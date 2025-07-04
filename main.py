from subscriber import MessageSubscriber
from message_processor import MessageProcessor
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

def main():
    message_queue = Queue()
    processor = MessageProcessor(message_queue)
    subscriber = MessageSubscriber(message_queue)
    
    with ThreadPoolExecutor(2) as executor:
        processor_future = executor.submit(processor.run)
        subscriber_futures = executor.submit(subscriber.run)

if __name__ == '__main__':
    
    main()