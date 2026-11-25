import statistics
import time

import httpx

BASE = "http://localhost:8000"
ROUNDS = 40
CASES = [
    ("unknown e-mail", "nobody@example.com"),
    ("known e-mail", "aigerim@example.com"),
]

samples = {name: [] for name, _ in CASES}
with httpx.Client(base_url=BASE) as client:
    for _ in range(ROUNDS):
        for name, email in CASES:  # alternate the cases: noise is shared equally
            start = time.perf_counter()
            response = client.post(
                "/auth/login",
                data={"username": email, "password": "wrong-password-123"},
            )
            samples[name].append((time.perf_counter() - start) * 1000)
            assert response.status_code == 401

print(f"wrong password, {ROUNDS} requests per case")
for name, values in samples.items():
    print(f"{name:<15} median {statistics.median(values):6.1f} ms")
