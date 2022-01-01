# import asyncio
from aiohttp import ClientSession
import time
import asyncio
import urllib
# import requests
#session = aiohttp.ClientSession()
#import requests_cache
#requests_cache.install_cache(cache_name='imdb_cache', backend='sqlite', expire_after=3600000)
sleep_time = 30

urls_cache = {}
base_url = 'https://www.imdb.com/'
async def get_url(url: str, session: ClientSession):
    global sleep_time
    # url = urllib.parse.urljoin(base_url, url)
    print(f'visit: {url}')
    
    while True:
        try:
            async with session.get(url) as response:
                response = await session.get(url)
                # sleep_time = 1
            
                if response.status != 200:
                    print(f'url: {url}')
                    print(f'Status: {response.status}\n Body: {await response.text()}')
                    print(f'Sleep: {sleep_time}')
                    await asyncio.sleep(sleep_time)
                    # sleep_time *= 2
                    continue
                else:
                    return await response.text()
        except Exception as ex:
                print(f'url: {url}')
                print(f'Exception: {ex}')
                print(f'Sleep: {sleep_time}')
                await asyncio.sleep(sleep_time)
                # sleep_time *= 2
                continue

