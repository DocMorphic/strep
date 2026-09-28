"""Run the unchanged upstream CLI with exact cached text conditioning injected."""
import os
from kimodo import load_model
from kimodo.scripts import generate
from embedding_cache import CachedEncoder

encoder = CachedEncoder(os.environ['STREP_EMBEDDING_MANIFEST'])


def load_with_cache(*args, **kwargs):
    return load_model(*args, text_encoder=encoder, **kwargs)


if __name__ == '__main__':
    generate.load_model = load_with_cache
    generate.main()
