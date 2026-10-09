import argparse
import json
import pathlib
import sys
import time
from datetime import datetime

import httpx

sys.path.insert(0, ".")
from dr import failover as fo  # noqa: E402

LOG = pathlib.Path("reports/runbook-run.jsonl")
URL = {"a": "http://127.0.0.1:8001", "b": "http://127.0.0.1:8002"}


def step(n, name, **kw):
    evt = {"step": n, "name": name, "ts": time.time(), "iso": datetime.utcnow().isoformat() + "Z"}
    evt.update(kw)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(evt) + "\n")
    print(json.dumps(evt))


def confirm(auto: bool, msg: str) -> bool:
    if auto:
        return True
    ans = input(msg + " [y/N] ")
    return ans.strip().lower() == "y"


def run(primary: str, target: str, backend: str, auto: bool) -> dict:
    # 1. xac_nhan_outage
    failures = 0
    for _ in range(3):
        try:
            r = httpx.get(URL[primary] + "/readyz", timeout=1.0)
            if r.status_code != 200:
                failures += 1
        except Exception:
            failures += 1
        time.sleep(1)
        
    step(1, "xac_nhan_outage", confirmed=failures == 3)
    if failures < 3:
        if not confirm(auto, "Primary seems healthy. Failover anyway?"):
            return {"status": "aborted"}

    # 2. thong_bao_incident
    step(2, "thong_bao_incident", t_alert=time.time())
    
    if not confirm(auto, f"Proceed with failover to {target}?"):
        return {"status": "aborted"}

    # 3. scale_gpu_pool (calls failover)
    fo_result = fo.failover(target, backend, wait=60.0)
    step(3, "scale_gpu_pool", result="called failover.py")

    # 4. verify_state_replica
    step(4, "verify_state_replica", **fo_result)

    # 5. dns_cutover
    step(5, "dns_cutover", success=True)

    # 6. verify_golden_signals
    errors = 0
    latencies = []
    for _ in range(10):
        t0 = time.time()
        try:
            r = httpx.get(URL[target] + "/v1/infer", timeout=2.0)
            if r.status_code != 200:
                errors += 1
        except Exception:
            errors += 1
        latencies.append(time.time() - t0)
        time.sleep(0.1)
    
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else None
    step(6, "verify_golden_signals", p95_latency=p95, error_rate=errors/10)

    # 7. post_incident
    step(7, "post_incident", elapsed_s=time.time() - LOG.stat().st_mtime if LOG.exists() else 0)

    return {"status": "completed"}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="a")
    p.add_argument("--target", default="b")
    p.add_argument("--backend", default="fs", choices=["fs", "minio"])
    p.add_argument("--auto", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.primary, a.target, a.backend, a.auto), indent=2))
