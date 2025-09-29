import os
import redis
from urllib.parse import urlparse

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
parsed_url = urlparse(redis_url)

redis_client = redis.Redis(
    host=parsed_url.hostname,# type: ignore
    port=parsed_url.port,  # type: ignore
    db=int(parsed_url.path.replace("/", "")),
    password=parsed_url.password,
    decode_responses=True
)