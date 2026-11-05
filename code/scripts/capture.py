#!/usr/bin/env python3
"""Re-capture one Track 1 scenario in the lab; requires explicit confirmation.

Outputs go to ignored captures/reproduced/, never over committed evidence.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from evaluate import ROOT, load_manifest


def find_capture(manifest: dict, capture_id: str) -> dict:
    for entry in manifest["captures"]:
        if entry.get("capture_id") == capture_id and entry.get("capture_recipe"):
            return entry
    raise ValueError(f"no Track 1 capture recipe with ID {capture_id!r}")


def _safe_path(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError("capture output must remain inside the repository")
    return resolved


def capture(manifest: dict, capture_id: str, *, output: Path | None = None,
            force: bool = False, wait_seconds: float | None = None) -> Path:
    settings = manifest.get("lab_settings", {})
    entry = find_capture(manifest, capture_id)
    recipe = entry["capture_recipe"]
    output = output or (ROOT / "captures" / "reproduced" / f"{capture_id}.pcap")
    if not output.is_absolute():
        output = ROOT / output
    output = _safe_path(ROOT, output)
    if output.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {output}; choose --output or pass --force")
    output.parent.mkdir(parents=True, exist_ok=True)

    runtime_settings = dict(settings)
    runtime_settings["results_dir"] = "results/reproduced"
    runtime_settings["pcap_dir"] = str(output.parent.relative_to(ROOT))
    runtime_settings["output_pcap"] = str(output.relative_to(ROOT))
    interface = runtime_settings.get("interface", "eth0")
    keylog_path = ROOT / settings.get("keylog_dir", "captures/keylogs") / f"{capture_id}.keylog"
    environment = dict(os.environ)
    if recipe.get("keylog"):
        keylog_path.parent.mkdir(parents=True, exist_ok=True)
        environment["SSLKEYLOGFILE"] = str(keylog_path)

    log_dir = ROOT / "results" / "reproduced" / "capture_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{capture_id}.log"
    wait = wait_seconds if wait_seconds is not None else float(settings.get("wait_seconds", 2))
    tcpdump = None
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"capture_id={capture_id}\noutput={output.relative_to(ROOT)}\n")
        log.write(f"filter={recipe['filter']}\nrepeat={recipe.get('repeat', 1)}\n")
        try:
            for command in recipe.get("setup", []):
                rendered = command.format(**runtime_settings)
                log.write(f"$ {rendered}\n")
                result = subprocess.run(rendered, shell=True, cwd=ROOT, env=environment,
                                        stdout=log, stderr=subprocess.STDOUT, check=False)
                if result.returncode != 0:
                    raise RuntimeError(f"setup command failed ({result.returncode}): {rendered}")

            tcpdump_argv = ["tcpdump", "-i", interface, "-U", "-w", str(output), recipe["filter"]]
            log.write("$ " + shlex.join(tcpdump_argv) + "\n")
            log.flush()
            tcpdump = subprocess.Popen(tcpdump_argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            time.sleep(wait)
            if tcpdump.poll() is not None:
                raise RuntimeError(f"tcpdump exited before client launch (status {tcpdump.returncode})")

            command = recipe["command"].format(**runtime_settings)
            for index in range(int(recipe.get("repeat", 1))):
                log.write(f"$ [{index + 1}/{recipe.get('repeat', 1)}] {command}\n")
                log.flush()
                result = subprocess.run(command, shell=True, cwd=ROOT, env=environment,
                                        stdout=log, stderr=subprocess.STDOUT, check=False)
                if result.returncode != 0:
                    raise RuntimeError(f"client command failed ({result.returncode}) on repetition {index + 1}")
            time.sleep(wait)
        finally:
            if tcpdump is not None and tcpdump.poll() is None:
                tcpdump.terminate()
                try:
                    tcpdump.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    tcpdump.kill()
                    tcpdump.wait()
    if not output.is_file():
        raise RuntimeError(f"tcpdump did not create {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wait-seconds", type=float)
    parser.add_argument("--force", action="store_true", help="replace the selected reproduction output")
    parser.add_argument("--confirm-network", action="store_true",
                        help="confirm that this command will generate real network traffic")
    args = parser.parse_args()
    if not args.confirm_network:
        parser.error("pass --confirm-network to authorize a live client request and packet capture")
    try:
        output = capture(load_manifest(), args.capture_id, output=args.output,
                         force=args.force, wait_seconds=args.wait_seconds)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"capture error: {exc}", file=sys.stderr)
        return 1
    print(f"saved reproduction (not registered evidence): {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
