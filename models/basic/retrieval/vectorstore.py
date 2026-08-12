import json
import os

import faiss
import numpy as np

from .embedder import embed

def _load():
    pass

def search_benchmark(query: str, k: int = 3) -> list[dict]:
    pass