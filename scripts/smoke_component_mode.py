import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REQUIRED_ENDPOINTS = [
    "/",
    "/app/static/health.txt",
    "/app/static/viewer/index.html",
]

OPTIONAL_ENDPOINTS = [
    "/static/health.txt",
]


def npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def run_cmd(args: list[str], cwd: Path) -> None:
    result = subprocess.run(args, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}")


def fetch_status(url: str, timeout: float = 5.0) -> int:
    with urlopen(url, timeout=timeout) as response:
        return int(response.getcode() or 0)


def wait_for_endpoint(url: str, deadline: float) -> int:
    last_error = ""
    while time.time() < deadline:
        try:
            status = fetch_status(url)
            if status == 200:
                return status
            last_error = f"HTTP {status}"
        except URLError as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url}. Last error: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for component mode no-proxy startup.")
    parser.add_argument("--port", type=int, default=8765, help="Port for temporary Streamlit run")
    parser.add_argument("--startup-timeout", type=int, default=60, help="Startup timeout in seconds")
    parser.add_argument("--skip-build", action="store_true", help="Skip npm build:streamlit-static")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    viewer_root = repo_root / "Dashboard" / "ifc-lite"

    if not args.skip_build:
        print("[1/4] Building and syncing viewer assets to Dashboard/static/viewer")
        run_cmd([npm_executable(), "run", "build:streamlit-static"], cwd=viewer_root)
    else:
        print("[1/4] Skipping viewer build step")

    env = os.environ.copy()
    env["VIEWER_EMBED_MODE"] = "component"
    env.setdefault("COMPONENT_SERVE_MODE", "streamlit-static")

    print(f"[2/4] Starting Streamlit on 127.0.0.1:{args.port} in component mode")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "Dashboard/app_with_viewer.py",
        "--server.port",
        str(args.port),
        "--server.address",
        "127.0.0.1",
    ]
    process = subprocess.Popen(cmd, cwd=str(repo_root), env=env)

    base_url = f"http://127.0.0.1:{args.port}"
    deadline = time.time() + args.startup_timeout

    try:
        print("[3/4] Verifying required endpoints")
        for endpoint in REQUIRED_ENDPOINTS:
            url = f"{base_url}{endpoint}"
            status = wait_for_endpoint(url, deadline=deadline)
            print(f"  OK {endpoint} -> {status}")

        print("[4/4] Verifying optional endpoints")
        for endpoint in OPTIONAL_ENDPOINTS:
            url = f"{base_url}{endpoint}"
            try:
                status = fetch_status(url)
                print(f"  OK {endpoint} -> {status}")
            except Exception as exc:  # noqa: BLE001
                print(f"  WARN {endpoint} -> {exc}")

        print("SMOKE TEST PASSED")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
