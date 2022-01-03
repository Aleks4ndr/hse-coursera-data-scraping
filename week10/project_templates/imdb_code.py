# define helper functions if needed
# and put them in `imdb_helper_functions` module.
# you can import them and use here like that:
from asyncio.tasks import gather
import multiprocessing as mp
import time
from bs4 import BeautifulSoup
import urllib
from imdb_helper_functions import get_url
from functools import lru_cache
import queue
from multiprocessing import Pool
import aiohttp
import asyncio
import requests
import lxml
import cchardet
import datetime
import logging
from asyncio_throttle import Throttler

cache = {}

def get_actors_by_movie_soup(cast_page_soup: BeautifulSoup, num_of_actors_limit=None):
    
    actors=[]
    cast_list = cast_page_soup.find('table', attrs={'class':'cast_list'})

    for row in cast_list.find_all('tr'):
        columns = row.find_all('td')

        if len(columns) == 4:
            actor = columns[1].find_next('a')
            actor_name = actor.get_text().strip()
            actor_url = actor.attrs['href']
            actors.append((actor_name, actor_url))

            if len(actors) == num_of_actors_limit:
                break
    
    return actors

def get_movies_by_actor_soup(actor_page_soup: BeautifulSoup, num_of_movies_limit=None):
    filmography = actor_page_soup.find('div', attrs={'class':'filmo-category-section'})

    movies = []
    for movie in filmography.find_all('div', attrs={'class':'filmo-row'}):
        refs = movie.find_all('a')
        if len(refs) == 1 and refs[0].parent.next_sibling.text.strip() == '':
            
            movie = refs[0]
            movies.append((movie.get_text(), movie.attrs['href'] + 'fullcredits'))

            if len(movies) == num_of_movies_limit:
                break

    return movies

@lru_cache(maxsize=None)
def get_movies_by_actor_url(url, num_of_movies_limit=None):
    page_text = get_url(url)
    soup = BeautifulSoup(page_text, features="lxml")
    return get_movies_by_actor_soup(soup, num_of_movies_limit)

def get_movies_by_actor_page(page_text, num_of_movies_limit=None):
    soup = BeautifulSoup(page_text, features="lxml")
    return get_movies_by_actor_soup(soup, num_of_movies_limit)

@lru_cache(maxsize=None)
def get_actors_by_movie_url(url, num_of_actors_limit=None):
    page_text = get_url(url)
    soup = BeautifulSoup(page_text, features="lxml")
    return get_actors_by_movie_soup(soup, num_of_actors_limit)

def get_actors_by_movie_page(page_text, num_of_actors_limit=None):
    soup = BeautifulSoup(page_text, features="lxml")
    return get_actors_by_movie_soup(soup, num_of_actors_limit)

def get_movie_distance(actor_start_url, actor_end_url,
        num_of_actors_limit=None, num_of_movies_limit=None):
    
    base_url = 'https://www.imdb.com/'
    start_url = urllib.parse.urlparse(actor_start_url).path + '/'
    end_url = urllib.parse.urlparse(actor_end_url).path + '/'

    visited_urls = set() 
    movies_queue = queue.Queue()
    actors_queue = queue.Queue()

    actors_queue.put(start_url)

    distance = 0
    while not (actors_queue.empty() and movies_queue.empty()):   
        while not actors_queue.empty():
            actor_url = actors_queue.get()
            visited_urls.add(actor_url)

            url = urllib.parse.urljoin(base_url, actor_url)
            actor_movies = get_movies_by_actor_url(url, num_of_actors_limit)

            for movie, movie_url in actor_movies:
                if movie_url in visited_urls:
                    continue
                
                movies_queue.put(movie_url)

        distance += 1

        while not movies_queue.empty():
            movie_url = movies_queue.get()
            visited_urls.add(movie_url)

            url = urllib.parse.urljoin(base_url, movie_url) + 'fullcredits'
            movie_actors = get_actors_by_movie_url(url, num_of_movies_limit)

            for actor, actor_url in movie_actors:
                if actor_url in visited_urls:
                    continue

                if actor_url == end_url:
                    return distance
                
                actors_queue.put(actor_url)

def process_responce(jobs_queue: mp.Queue, actor_movies_queue: mp.Queue, movie_actors_queue: mp.Queue):

    while True:
        command, url, data = jobs_queue.get()

        if command == 1:
            actor_movies = get_movies_by_actor_page(data)
            actor_movies_queue.put((url, actor_movies))
        elif command == 2:
            movie_actors = get_actors_by_movie_page(data)
            movie_actors_queue.put((url, movie_actors))
        else:
            return

async def get_movie_distance_async(actor_start_url, actor_end_url,
        num_of_actors_limit=None, num_of_movies_limit=None):
    
    base_url = 'https://www.imdb.com/'
    start_url = urllib.parse.urlparse(actor_start_url).path + '/'
    end_url = urllib.parse.urlparse(actor_end_url).path + '/'

    visited_urls = set() 
    movies_queue = set()
    actors_queue = set()
    
    manager = mp.Manager()
    # jobs_queue = manager.Queue()
    jobs_queue = mp.Queue()
    actor_movies_queue = manager.Queue()
    movie_actors_queue = manager.Queue()

    actors_queue.add(start_url)

    distance = 0

    # workers_count = mp.cpu_count() - 2
    workers_count = 3

    workers: list[mp.Process] = []
    for _ in range(workers_count):
        worker = mp.Process(target=process_responce, args=(jobs_queue, actor_movies_queue, movie_actors_queue))
        worker.start()
        workers.append(worker)

    headers = {
        'Accept-Language':'en',
        'X-FORWARDED-FOR':'2.21.184.0'
    }
    throttler = Throttler(rate_limit=3)
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(base_url=base_url, headers=headers, connector=connector, timeout=timeout) as session:
  
        while len(actors_queue) + len(movies_queue) > 0:
            movies_queue = set()
            actors_queue -= visited_urls

            for actor in list(actors_queue):
                data = cache.get(actor, None)
                if type(data) == list:
                    movies_queue.update(data)
                    actors_queue -= actor

            await asyncio.gather(*[get_url(actor_url, session, throttler, jobs_queue, 1) for actor_url in actors_queue])
            visited_urls |= actors_queue

            # print(f'{datetime.datetime.now().ctime()} srart processing of {len(actors_pages)} actors')
            # data = pool.map(get_movies_by_actor_page, actors_pages)
            # print(f'{datetime.datetime.now().ctime()} finish processing of {len(actors_pages)} actors')
            
            data = [actor_movies_queue.get() for _ in actors_queue]           
            cache.update(dict(data))

            # flatten array and update movies queue
            movies_queue.update([a[1] for b in data for a in b[1]])

            distance += 1

            actors_queue = set()
            movies_queue -= visited_urls
            for movie in list(movies_queue):
                data = cache.get(movie, None)
                if type(data) == list:
                    actors_queue.update(data)
                    movies_queue -= movie

            await asyncio.gather(*[get_url(movie_url, session, throttler, jobs_queue, 2) for movie_url in movies_queue])
            visited_urls |= movies_queue

            # print(f'{datetime.datetime.now().ctime()} srart processing of {len(movies_pages)} movies')
            # data = pool.map(get_actors_by_movie_page, movies_pages)
            # print(f'{datetime.datetime.now().ctime()} finish processing of {len(movies_pages)} movies')
            data = [movie_actors_queue.get() for _ in movies_queue]
            cache.update(dict(data))

            # flatten array and update actors queue
            actors_queue.update([a[1] for b in data for a in b[1]])

            # stop jobs if result is found and return distance
            if end_url in actors_queue:
                for worker in workers:
                    jobs_queue.put((None, None, None))

                for worker in workers:
                    worker.join()
                
                return distance

            # stop jobs if distance > 4 and return 5
            if distance == 4:
                for worker in workers:
                    jobs_queue.put((None, None, None))

                for worker in workers:
                    worker.join()

                return 5

            

def get_movie_descriptions_by_actor_soup(actor_page_soup):
    # your code here
    return # your code here

# async def get_movie_distance_async(actor_start_url, actor_end_url,
#         num_of_actors_limit=None, num_of_movies_limit=None):


#         cache = {}
#         actors_urls = [actor_start_url]
#         with aiohttp.ClientSession() as session:


async def main():
    global cache
    cache = dict()

    actors_pairs_full = [
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Dwayne Johnson', 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Chris Hemsworth', 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Robert Downey Jr.', 'https://www.imdb.com/name/nm0000375?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd'),
        ('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd')),
        (('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd'),
        ('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd')),
        (('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd'),
        ('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd')),
        (('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Akshay Kumar', 'https://www.imdb.com/name/nm0474774?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd'),
        ('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd')),
        (('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd'),
        ('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd')),
        (('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Jackie Chan', 'https://www.imdb.com/name/nm0000329?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd'),
        ('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd')),
        (('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Bradley Cooper', 'https://www.imdb.com/name/nm0177896?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd'),
        ('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0')),
        (('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Adam Sandler', 'https://www.imdb.com/name/nm0001191?ref_=nmls_hd'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0'),
        ('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0')),
        (('Scarlett Johansson',
        'https://www.imdb.com/name/nm0424060/?ref_=nv_sr_srsg_0'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd')),
        (('Sofia Vergara', 'https://www.imdb.com/name/nm0005527/?ref_=nv_sr_srsg_0'),
        ('Chris Evans.', 'https://www.imdb.com/name/nm0262635?ref_=nmls_hd'))
    ]

    distances = {}
    for pair in actors_pairs_full[:3]:
        actor_start = pair[0][0]
        actor_end = pair[1][0]
        actor_start_url = pair[0][1]
        actor_end_url = pair[1][1]
        distance = await get_movie_distance_async(actor_start_url, actor_end_url)
        distances[(actor_start, actor_end)] = distance
        print(distances)
    # urls = [a[0][1] for a in actors_pairs_full]
    
    # actor_start_url = 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'
    # actor_end_url = 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'
    # asyncio.run(get_movie_distance_async(actor_start_url, actor_end_url))



def test1():
    headers = {
        'Accept-Language':'en',
        'X-FORWARDED-FOR':'2.21.184.0'
    }
    url = 'https://www.imdb.com/title/tt5179598/fullcredits'
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, features="lxml")
    print(get_actors_by_movie_soup(soup))
    print(get_actors_by_movie_soup(soup, 10))

if __name__ == '__main__':
    # logger = mp.log_to_stderr()
    # logger.setLevel(mp.SUBDEBUG)
    asyncio.run(main())
    # import cProfile
    # print(cProfile.__file__)
    # cProfile.run("test1()", "app2.profile")

    # main()
    # asyncio.run(main)
    # event_loop = asyncio.get_event_loop()
    
    # headers = {
    #     'Accept-Language':'en',
    #     'X-FORWARDED-FOR':'2.21.184.0'
    # }
    # url = 'https://www.imdb.com/title/tt5179598/fullcredits'
    # response = requests.get(url, headers=headers)
    # soup = BeautifulSoup(response.text, features="lxml")
    # print(get_actors_by_movie_soup(soup))
    # print(get_actors_by_movie_soup(soup, 10))

    # # #url = 'https://www.imdb.com/name/nm5052065'
    # url = 'https://www.imdb.com/name/nm0695435/'
    # response = requests.get(url, headers=headers)
    # soup = BeautifulSoup(response.text, features="lxml")
    # print(get_movies_by_actor_soup(soup))
    # print(get_movies_by_actor_soup(soup, 5))

    # actor_start_url = 'https://www.imdb.com/name/nm0695435?ref_=tt_cl_t_1'
    # actor_end_url = 'https://www.imdb.com/name/nm2088803?ref_=tt_cl_t_2'
    # distance = get_movie_distance(actor_start_url, actor_end_url)

    # print(f'distance between {actor_start_url} and {actor_end_url} = {distance}')


    # actor_end_url = 'https://www.imdb.com/name/nm0425005?ref_=nmls_hd'
    # actor_end_url = 'https://www.imdb.com/name/nm1165110?ref_=nmls_hd'
    # distance = get_movie_distance(actor_start_url, actor_end_url, 10, 10)

    # print(f'distance between {actor_start_url} and {actor_end_url} = {distance}')



