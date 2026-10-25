"""Run the complete G04 simulation and verification with the current Python."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="Use a separate result directory; leave the website export unchanged")
    args = parser.parse_args()
    problems = []
    for line in (HERE / "requirements.txt").read_text(encoding="utf-8").splitlines():
        package, expected = line.split("==")
        try:
            actual = version(package)
        except PackageNotFoundError:
            actual = "missing"
        if actual != expected:
            problems.append(f"{package}: {actual}, required {expected}")
    if problems:
        parser.exit(2, "Dependency check failed:\n" + "\n".join(problems)
                    + "\nInstall code/ch04_exercises/raman/requirements.txt using this Python.\n")

    output = (args.output if args.output else HERE / "outputs").resolve()
    target = output / "ch04-results.js" if args.output else ROOT / "assets/js/ch04-results.js"
    logdir = output / "reproduction_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    receipt = output / "reproduction_record.json"
    steps = [
        ("main_case", [HERE / "exercise.py", "--output", output]),
        ("extensions", [HERE / "extensions.py", "--output", output]),
        ("calibration", [HERE.parent / "03_probability_calibration.py", "--output", output / "calibration.json"]),
        ("web_export", [HERE / "export_interactive.py", "--output", output, "--target", target]),
        ("verification", [HERE / "verify.py", "--output", output, "--interactive-data", target]),
    ]
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", MPLBACKEND="Agg")
    # Small matrices run more predictably without excessive BLAS threads.
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        env[name] = "1"
    record = {"started_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "output": str(output),
              "interactive_data": str(target), "status": "running", "steps": []}
    def save():
        receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save()
    for index, (name, arguments) in enumerate(steps, 1):
        command = [sys.executable, *map(str, arguments)]
        logfile = logdir / f"{index:02d}_{name}.log"
        print(f"[{index}/{len(steps)}] {name}: {logfile}", flush=True)
        started = time.perf_counter()
        with logfile.open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        record["steps"].append({"name": name, "command": command,
                                "exit_code": result.returncode,
                                "seconds": round(time.perf_counter() - started, 3),
                                "log": str(logfile)})
        if result.returncode:
            record["status"] = "failed"
            save()
            parser.exit(1, f"Stopped at {name}. Inspect {logfile}\n")
        save()
    record["status"] = "passed"
    record["finished_utc"] = datetime.now(timezone.utc).isoformat()
    save()
    print(f"PASS: all five stages completed. Record: {receipt}")


if __name__ == "__main__":
    main()
