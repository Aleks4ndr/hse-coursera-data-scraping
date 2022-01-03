# import cProfile
# import imdb_code
import time
import asyncio
import multiprocessing as mp

# cProfile.run("imdb_code.test1()", "app.profile")

async def get_data(name, queue):
    time.sleep(1)
    queue.put(name)

def worker(queue: mp.Queue, flag: mp.Value, name):

    while flag.value != 0:
        task = queue.get()
        print(f'worker({name}) - processing queue {task}')
        time.sleep(1)

    print(f'worker {name} exit')


async def main():
    queue1 = mp.Queue()
    queue2 = mp.Queue()
    flag = mp.Value('i', 1)

    worker1 = mp.Process(target=worker, args=(queue1, flag, 'worker1'))
    worker2 = mp.Process(target=worker, args=(queue1, flag, 'worker2'))
    worker3 = mp.Process(target=worker, args=(queue2, flag, 'worker3'))
    worker4 = mp.Process(target=worker, args=(queue2, flag, 'worker4'))

    worker1.start()
    worker2.start()
    worker3.start()
    worker4.start()

    for i in range(3):
        await asyncio.gather(
            *[get_data(f'iteration {i} task1 {j}', queue1) for j in range(5)]
        )

        while not queue1.empty():
            time.sleep(1)

        await asyncio.gather(
            *[get_data(f'iteration {i} task2 {j}', queue2) for j in range(5)]
        )

        while not queue2.empty():
            time.sleep(1)


    flag.value = 0

    worker1.join()
    worker2.join()
    worker3.join()
    worker4.join()

    print("programm exited")


if __name__ == "__main__":
    asyncio.run(main())