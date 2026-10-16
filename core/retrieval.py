"""Dependency-free BM25 over the chunks of one shipment."""
import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return TOKEN.findall(text.lower())


class BM25:
    def __init__(self, texts, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(c.values()) for c in self.docs]
        self.avg = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        df = Counter()
        for c in self.docs:
            df.update(c.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query):
        terms = tokenize(query)
        out = []
        for i, c in enumerate(self.docs):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / (self.avg or 1))
            for t in terms:
                f = c.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

    def top(self, query, k=3):
        scored = self.scores(query)
        ranked = sorted(range(len(scored)), key=lambda i: -scored[i])
        return [i for i in ranked[:k] if scored[i] > 0]
