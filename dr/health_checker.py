import argparse
import json
import pathlib
import time
from datetime import datetime

import httpx

URL = {"a": "http://127.0.0.1:8001", "b": "http://127.0.0.1:8002"}

def probe(region: str, timeout: float) -> tuple[bool, str]:
    try:
        r = httpx.get(URL[region] + "/readyz", timeout=timeout)
        if r.status_code == 200:
            return True, "OK"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def run(interval: float, timeout: float, threshold: int, duration: float, out: pathlib.Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    
    # State tracking
    state = {"a": "HEALTHY", "b": "HEALTHY"}
    fail_count = {"a": 0, "b": 0}
    
    with out.open("a") as f:
        while time.time() - start < duration:
            for r in ["a", "b"]:
                ok, reason = probe(r, timeout)
                
                if ok:
                    fail_count[r] = 0
                    if state[r] == "UNHEALTHY":
                        state[r] = "HEALTHY"
                        evt = {
                            "event": "state_change",
                            "ts": time.time(),
                            "iso": datetime.utcnow().isoformat() + "Z",
                            "region": r,
                            "to": "HEALTHY",
                            "reason": reason,
                            "interval_s": interval,
                            "threshold": threshold, "consecutive_fails": fail_count[r]
                        }
                        f.write(json.dumps(evt) + "\n")
                        f.flush()
                else:
                    fail_count[r] += 1
                    if state[r] == "HEALTHY" and fail_count[r] >= threshold:
                        state[r] = "UNHEALTHY"
                        evt = {
                            "event": "state_change",
                            "ts": time.time(),
                            "iso": datetime.utcnow().isoformat() + "Z",
                            "region": r,
                            "to": "UNHEALTHY",
                            "reason": reason,
                            "interval_s": interval,
                            "threshold": threshold, "consecutive_fails": fail_count[r]
                        }
                        f.write(json.dumps(evt) + "\n")
                        f.flush()
                        
            time.sleep(interval)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--threshold", type=int, default=3)
    p.add_argument("--duration", type=float, default=300)
    p.add_argument("--out", default="reports/health-events.jsonl")
    a = p.parse_args()
    run(a.interval, a.timeout, a.threshold, a.duration, pathlib.Path(a.out))
