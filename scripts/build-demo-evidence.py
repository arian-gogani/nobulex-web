#!/usr/bin/env python3
"""Capture the existing fictional registry demo, without redefining its inputs."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import types

sys.dont_write_bytecode = True
FILES = ("suite/harness.py", "examples/wrong_window.py")
EXPECTED = [("PASS", None), ("FAIL_UNSAFE", "partial_truncation"),
            ("INDETERMINATE", None)]


def capture(registry):
    # Linked-worktree hooks can export git context for a different checkout.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(registry), *args], env=env,
            stderr=subprocess.PIPE)

    commit = git("rev-parse", "HEAD").decode().strip()
    if Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve() != registry:
        raise ValueError("registry path must be the repository root")
    sources = {}
    for name in FILES:
        data = (registry / name).read_bytes()
        if data != git("show", f"{commit}:{name}"):
            raise ValueError(f"refusing modified source: {name} differs from HEAD")
        sources[name] = data

    # Execute exactly the verified bytes. The demo imports this real harness.
    harness = types.ModuleType("harness")
    harness.__file__ = str(registry / FILES[0])
    exec(compile(sources[FILES[0]], harness.__file__, "exec"), harness.__dict__)
    classify = harness.classify_truncation
    cases = []

    def observed(subject, reference):
        inputs = copy.deepcopy({"subject": subject, "reference": reference})
        outcome, cause, reason = classify(subject, reference)
        cases.append({**inputs, "outcome": outcome, "cause": cause,
                      "raw_reason": reason,
                      "count_equal": len(subject) == len(reference)})
        return outcome, cause, reason

    harness.classify_truncation = observed
    old_harness = sys.modules.get("harness")
    old_path = sys.path[:]
    sys.modules["harness"] = harness
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        namespace = {"__name__": "captured_demo",
                     "__file__": str(registry / FILES[1])}
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(compile(sources[FILES[1]], namespace["__file__"], "exec"), namespace)
            result = namespace["main"]()
    finally:
        sys.path[:] = old_path
        if old_harness is None:
            sys.modules.pop("harness", None)
        else:
            sys.modules["harness"] = old_harness
    if result != 0:
        raise ValueError(f"demo main failed: exit {result}; {stderr.getvalue()}")
    if [(c["outcome"], c["cause"]) for c in cases] != EXPECTED:
        raise ValueError("demo did not produce the three expected outcomes and causes")
    for name, data in sources.items():
        if (registry / name).read_bytes() != data:
            raise ValueError(f"source changed during capture: {name}")
    if git("rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("HEAD changed during capture")
    return {
        "schema": "nobulex-fictional-demo-v1",
        "evidence_type": "fictional_precomputed_classifier_demonstration",
        "issued_registry_record": False,
        "live_provider_assessment": False,
        "source": {
            "repository": "https://github.com/arian-gogani/nobulex-registry",
            "commit": commit,
            "file_sha256": {name: hashlib.sha256(data).hexdigest()
                            for name, data in sources.items()},
        },
        "runtime": {"python_version": platform.python_version(),
                    "python_implementation": platform.python_implementation()},
        "reproduction": {
            "working_directory": "root of the registry repository at source.commit",
            "command": "python3 examples/wrong_window.py",
            "capture_method": "Called that script's main() with the real classifier wrapped to capture arguments and return values.",
            "exit_code": result,
        },
        "cases": cases,
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "limits": [
            "All inputs are fictional; no MCP request, network call or provider assessment was made.",
            "The raw reason about a same-upstream direct read describes the modeled fixture comparison; no upstream was contacted.",
            "PASS covers this truncation probe only and does not establish price accuracy or whole-tool correctness.",
            "The different-date window is unresolved by this probe, not a proven tool defect.",
            "Source hashes identify code bytes; they do not authenticate an issuer or prove a real observation occurred.",
            "This is a precomputed demo, not a customer assessment, issued record or independent customer rerun.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path, help="Local registry repository root")
    args = parser.parse_args()
    try:
        evidence = capture(args.registry.resolve())
        output = Path(__file__).resolve().parents[1] / "examples" / "wrong-window.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"Captured {len(evidence['cases'])} fictional cases: {output} ({output.stat().st_size} bytes)")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Evidence capture failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
