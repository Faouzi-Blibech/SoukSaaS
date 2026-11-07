"""Cross-platform task runner: python tasks.py setup|seed|run|dashboard|test|eval|demo"""
import subprocess
import sys

TASKS = {
    "setup": [["uv", "sync"]],
    "seed": [[sys.executable, "scripts/seed.py"]],
    "run": [[sys.executable, "-m", "uvicorn", "app.main:app", "--reload"]],
    "dashboard": [[sys.executable, "-m", "streamlit", "run", "dashboard/app.py"]],
    "test": [[sys.executable, "-m", "pytest", "-q"]],
}
NOT_IMPLEMENTED = {"eval", "demo"}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS | dict.fromkeys(NOT_IMPLEMENTED):
        print(f"usage: python tasks.py {'|'.join([*TASKS, *sorted(NOT_IMPLEMENTED)])}")
        return 2
    name = sys.argv[1]
    if name in NOT_IMPLEMENTED:
        print(f"{name}: not implemented yet (phase 6/7)")
        return 0
    for cmd in TASKS[name]:
        code = subprocess.call(cmd)
        if code:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
