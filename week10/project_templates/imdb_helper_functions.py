from aiohttp import ClientSession
import asyncio
import multiprocessing as mp
import aiohttp
from asyncio_throttle import Throttler
sleep_time = 30

async def get_url(url: str, session: ClientSession, throttler: Throttler, jobs_queue: mp.Queue, job_type: int):

    
    async with throttler:
        while True:
            try:
            
              async with session.get(url) as response:
                print(f'visit: {url}')
                response = await session.get(url)
            
                if response.status != 200:
                    print(f'url: {url}')
                    print(f'Status: {response.status}\n Body: {await response.text()}')
                    print(f'Sleep: {sleep_time}')
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    text = await response.text()
                    jobs_queue.put((job_type, url, text))
                    return text
            except TimeoutError as ex:
                    print(f'url: {url}')
                    print(f'Exception: TimeoutException')
                    print(f'Sleep: {sleep_time}')
                    await asyncio.sleep(sleep_time)
            except Exception as ex:
                    print(f'url: {url}')
                    print(f'Exception: {ex}')
                    print(f'Sleep: {sleep_time}')
                    # await asyncio.sleep(sleep_time)
                    continue

