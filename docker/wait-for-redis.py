import os, sys
if os.environ['PHENOMEDB_PATH'] not in sys.path:
   sys.path.append(os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config
from phenomedb.cache import Cache
import redis
import time

def attempt_redis_connection():
    try:
        redis_cache = redis.Redis(host=config['REDIS']['host'],
                              port=config['REDIS']['port'],
                              #username=config['REDIS']['user'],
                              password=config['REDIS']['password'])
    except Exception as err:
        print(err)
        time.sleep(5)
        redis_cache = attempt_redis_connection()

    return redis_cache

def attempt_cache_init():
    try:
        cache = Cache()
    except Exception as err:
        print(err)
        time.sleep(5)
        cache = attempt_cache_init()

    return cache

if __name__ == "__main__":
    print("Running wait-for-redis.py...")
    redis_cache = attempt_redis_connection()
    cache = attempt_cache_init()
    print("...Redis ready!")



