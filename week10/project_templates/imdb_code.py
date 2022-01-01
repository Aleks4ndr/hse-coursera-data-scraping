# define helper functions if needed
# and put them in `imdb_helper_functions` module.
# you can import them and use here like that:
from asyncio.tasks import gather
import multiprocessing
import time
from bs4 import BeautifulSoup
import urllib
import collections
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
            movies.append((movie.get_text(), movie.attrs['href']))

            if len(movies) == num_of_movies_limit:
                break

    return movies

@lru_cache(maxsize=None)
def get_movies_by_actor_url(url, num_of_movies_limit=None):
    page_text = get_url(url)
    soup = BeautifulSoup(page_text, features="html.parser")
    return get_movies_by_actor_soup(soup, num_of_movies_limit)

def get_movies_by_actor_page(page_text, num_of_movies_limit=None):
    soup = BeautifulSoup(page_text, features="lxml")
    return get_movies_by_actor_soup(soup, num_of_movies_limit)

@lru_cache(maxsize=None)
def get_actors_by_movie_url(url, num_of_actors_limit=None):
    page_text = get_url(url)
    soup = BeautifulSoup(page_text, features="html.parser")
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

async def get_movie_distance_async(actor_start_url, actor_end_url,
        num_of_actors_limit=None, num_of_movies_limit=None):
    
    base_url = 'https://www.imdb.com/'
    start_url = urllib.parse.urlparse(actor_start_url).path + '/'
    end_url = urllib.parse.urlparse(actor_end_url).path + '/'

    visited_urls = set() 
    movies_queue = set()
    actors_queue = set()
    
    actors_queue.add(start_url)

    distance = 0

    workers_count = multiprocessing.cpu_count() - 2

    headers = {
        'Accept-Language':'en',
        'X-FORWARDED-FOR':'2.21.184.0'
    }
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(base_url=base_url, headers=headers, connector=connector, timeout=timeout) as session:
      with Pool(workers_count) as pool:
  
        while len(actors_queue) + len(movies_queue) > 0:
            movies_queue = set()
            actors_queue -= visited_urls

            for actor in actors_queue:
                data = cache.get(actor, None)
                if type(data) == list:
                    movies_queue.update(data)
                    actors_queue -= actor

            actors_pages = await asyncio.gather(*[get_url(actor_url, session) for actor_url in actors_queue])
            visited_urls |= actors_queue

            print(f'{datetime.datetime.now().ctime()} srart processing of {len(actors_pages)} actors')
            data = pool.map(get_movies_by_actor_page, actors_pages)
            print(f'{datetime.datetime.now().ctime()} finish processing of {len(actors_pages)} actors')
            cache.update({actor_url:movies for actor_url, movies in zip(actors_queue, data)})

            movies_queue.update([a[1] for b in data for a in b])

            distance += 1

            actors_queue = set()
            movies_queue -= visited_urls
            for movie in movies_queue:
                data = cache.get(movie, None)
                if type(data) == list:
                    actors_queue.update(data)
                    movies_queue -= movie


            movies_pages = await asyncio.gather(*[get_url(movie_url + 'fullcredits', session) for movie_url in movies_queue])
            visited_urls |= movies_queue

            print(f'{datetime.datetime.now().ctime()} srart processing of {len(movies_pages)} movies')
            data = pool.map(get_actors_by_movie_page, movies_pages)
            print(f'{datetime.datetime.now().ctime()} finish processing of {len(movies_pages)} movies')

            cache.update({movie_url:movies for movie_url, movies in zip(movies_pages, data)})

            actors_queue.update([a[1] for b in data for a in b])

            if end_url in actors_queue:
                return distance

            if distance == 4:
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



