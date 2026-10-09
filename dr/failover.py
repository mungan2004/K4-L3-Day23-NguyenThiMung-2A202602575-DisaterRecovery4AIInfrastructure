import argparse
import json
import pathlib
import sys
import time
from datetime import datetime

import httpx

sys.path.insert(0, ".")
from state import snapshot  # noqa: E402

URL = {"a": "http://127.0.0.1:8001", "b": "http://127.0.0.1:8002"}
LOG = pathlib.Path("reports/failover-events.jsonl")


def emit(**kw):
    evt = kw.copy()
    evt["iso"] = datetime.utcnow().isoformat() + "Z"
    if "ts" not in evt:
        evt["ts"] = time.time()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(evt) + "\n")
    print(json.dumps(evt))


def failover(target: str, backend: str, wait: float) -> dict:
    # 1_verify_target
    try:
        r = httpx.get(URL[target] + "/v1/state")
        emit(step="1_verify_target", state=r.json())
    except Exception as e:
        emit(step="1_verify_target", error=str(e))

    # 2_restore_snapshot
    meta = snapshot.get(target, backend)
    primary = "a" if target == "b" else "b"
    primary_db = pathlib.Path(f"state/region-{primary}/vectors.sqlite")
    restored_db = pathlib.Path(f"state/region-{target}/vectors.sqlite")
    rpo_stats = snapshot.rpo(primary_db, restored_db)
    
    emit(step="2_restore_snapshot", 
         rpo_seconds=rpo_stats["rpo_seconds"], 
         docs_lost=rpo_stats["docs_lost"], 
         embed_model_version=meta.get("embed_model_version"))

    # 3_scale_pool
    p_state = pathlib.Path(f"state/region-{target}/pool_state")
    p_state.parent.mkdir(parents=True, exist_ok=True)
    p_state.write_text("full\n")
    emit(step="3_scale_pool", pool_state="full")

    # 4_wait_ready
    start = time.time()
    ready = False
    while time.time() - start < wait:
        try:
            r = httpx.get(URL[target] + "/readyz", timeout=1.0)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(1.0)
        
    if not ready:
        emit(step="4_wait_ready", success=False, error="timeout")
        raise RuntimeError("Target region failed to become ready")
        
    emit(step="4_wait_ready", success=True)

    # 5_dns_cutover
    pathlib.Path("edge/active_region").write_text(target + "\n")
    emit(step="5_dns_cutover", active_region=target)

    return {
        "rpo_seconds": rpo_stats["rpo_seconds"],
        "docs_lost": rpo_stats["docs_lost"],
        "embed_model_version": meta.get("embed_model_version")
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--target", default="b", choices=["a", "b"])
    p.add_argument("--backend", default="fs", choices=["fs", "minio"])
    p.add_argument("--wait", type=float, default=60)
    a = p.parse_args()
    try:
        print(json.dumps(failover(a.target, a.backend, a.wait), indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
