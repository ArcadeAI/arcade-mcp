from functools import lru_cache

from arcade.core.config_model import Config


@lru_cache(maxsize=1)
def get_config() -> Config:
    """
    Get the Arcade configuration.

    This function is cached, so subsequent calls will return the same Config object
    without reloading from the file, unless the cache is cleared.

    remember to clear the cache if the configuration file is modified.
    use `get_config.cache_clear()` to clear the cache.

    Returns:
        Config: The Arcade configuration.
    """
    return Config.load_from_file()


config = get_config()
