#!/usr/bin/env python3
"""Measure, gate, and log Gowin logic-reduction experiments.

Subcommands (run from anywhere inside the repo):
  freeze   [--name NAME]          Snapshot src/, gowin/, constraints/ as a fallback.
  restore  [--name NAME]          Copy a snapshot back over src/, gowin/, constraints/.
  gate                            Run scripts/run_regression.py; require all_passed.
  measure  --label TEXT [opts]    Fresh Gowin build, parse reports, append CSV row.
  parse    --reports DIR          Parse existing report files (no build).
  compare                         Show the log table, best-first by ranking order.

Ranking order used by the judges: total Logic, then Registers. BSRAM is free.
Never touches git. Never programs hardware. Never writes bitstream/.
"""
import argparse, csv, datetime, glob, hashlib, json, os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_GW_SH = r"C:\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe"
SNAP_DIRS = ["src", "gowin", "constraints"]
LOGIC_RE = r"\bLogic\s*\|?\s*(\d+)\s*(?:\(|/)"
LOG_FIELDS = ["time", "label", "logic", "lut", "alu", "ram16", "registers", "bsram",
              "pnr_logic", "gate", "verdict", "src_hash"]


def repo_root():
    p = Path.cwd().resolve()
    for d in [p, *p.parents]:
        if (d / "gowin" / "build_uart.tcl").exists() and (d / "src").is_dir():
            return d
    sys.exit("Run inside the repo (needs gowin/build_uart.tcl and src/).")


ROOT = repo_root()
OPT = ROOT / ".build" / "opt"
LOG = ROOT / "results" / "optimization_log.csv"


def src_hash():
    h = hashlib.sha256()
    for f in sorted((ROOT / "src").glob("*.v")):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()[:12]


def text_of(path):
    t = Path(path).read_text(errors="replace")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[ \t\r\n]+", " ", t)


def first_int(pattern, text, default=None, group=1):
    m = re.search(pattern, text)
    return int(m.group(group)) if m else default


def parse_reports(reports):
    """reports: directory searched recursively for Gowin synthesis/PnR outputs."""
    reports = Path(reports)
    syn = next(iter(sorted(reports.rglob("*_syn.rpt.html"))), None)
    if syn is None:
        sys.exit(f"No *_syn.rpt.html under {reports}")
    t = text_of(syn)
    r = {
        "logic": first_int(LOGIC_RE, t),
        "lut": first_int(r"(\d+)\s*LUT,", t),
        "alu": first_int(r"(\d+)\s*ALU(?:,|\))", t, 0),
        "ram16": first_int(r"(\d+)\s*RAM16\)", t, 0),
        "registers": first_int(r"\bRegister\s*\|?\s*(\d+)\s*/\s*\d+", t),
        "bsram": first_int(r"\bBSRAM\s*\|?\s*(\d+)", t, 0),
    }
    if r["logic"] is None or r["registers"] is None:
        sys.exit("Could not parse Logic/Register from synthesis report; inspect it by hand.")
    pnr = next(iter(sorted(reports.rglob("*.rpt.txt"))), None)
    r["pnr_logic"] = first_int(LOGIC_RE, text_of(pnr)) if pnr else None
    xml = next(iter(sorted(reports.rglob("*_syn_rsc.xml"))), None)
    r["modules"] = module_rows(xml) if xml else []
    return r


def module_rows(xml_path):
    rows = []
    def walk(node, depth):
        a = node.attrib
        rows.append((("  " * depth) + a.get("name", "?"), a.get("Lut", "-"), a.get("Alu", "-"),
                     a.get("Register", "-"), a.get("Ssram", "-"), a.get("Bsram", "-")))
        for c in node.findall("SubModule"):
            walk(c, depth + 1)
    walk(ET.parse(xml_path).getroot(), 0)
    return rows


def print_modules(rows):
    print(f"{'module (own cells)':<28}{'LUT':>6}{'ALU':>6}{'REG':>6}{'SSRAM':>7}{'BSRAM':>7}")
    for r in rows:
        print(f"{r[0]:<28}{r[1]:>6}{r[2]:>6}{r[3]:>6}{r[4]:>7}{r[5]:>7}")


def read_log():
    if not LOG.exists():
        return []
    with LOG.open(newline="") as f:
        return list(csv.DictReader(f))


def key(row):
    return (int(row["logic"]), int(row["registers"]))


def best_gated(rows):
    ok = [r for r in rows if r["gate"] == "pass"]
    return min(ok, key=key) if ok else None


def cmd_freeze(a):
    dst = OPT / (a.name or "baseline")
    if dst.exists():
        shutil.rmtree(dst)
    for d in SNAP_DIRS:
        shutil.copytree(ROOT / d, dst / d)
    print(f"Frozen {SNAP_DIRS} to {dst}  (src hash {src_hash()})")


def cmd_restore(a):
    srcdir = OPT / (a.name or "baseline")
    if not srcdir.exists():
        sys.exit(f"No snapshot at {srcdir}")
    for d in SNAP_DIRS:
        shutil.rmtree(ROOT / d)
        shutil.copytree(srcdir / d, ROOT / d)
    print(f"Restored {SNAP_DIRS} from {srcdir}")


def run_gate():
    proc = subprocess.run([sys.executable, "scripts/run_regression.py"], cwd=ROOT,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tail = "\n".join(proc.stdout.strip().splitlines()[-15:])
    ok = proc.returncode == 0
    try:
        ok = ok and json.loads((ROOT / "results" / "software_validation.json").read_text())["all_passed"] is True
    except Exception:
        ok = False
    return ok, tail


def cmd_gate(a):
    ok, tail = run_gate()
    print(tail)
    print("GATE:", "pass" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def cmd_measure(a):
    gate = "skipped"
    if not a.skip_gate:
        ok, tail = run_gate()
        gate = "pass" if ok else "fail"
        print(tail)
        print("GATE:", gate)
        if not ok:
            print("Regression failed. Logic is not worth measuring for a design that is wrong.")
    gw = a.gw_sh or os.environ.get("GOWIN_SH") or (DEFAULT_GW_SH if Path(DEFAULT_GW_SH).exists() else shutil.which("gw_sh"))
    if not gw:
        sys.exit("gw_sh not found. Pass --gw-sh PATH or set GOWIN_SH.")
    build = ROOT / ".build" / "gowin_trade"
    if not a.reuse_project and build.exists():
        shutil.rmtree(build)  # judges rebuild fresh; a cached project can hide new files
    env = dict(os.environ, UART_BUILD_FLOW=a.flow)
    proc = subprocess.run([gw, str(ROOT / "gowin" / "build_uart.tcl")], cwd=ROOT, env=env,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OPT).mkdir(parents=True, exist_ok=True)
    (OPT / "last_build.log").write_text(proc.stdout)
    if proc.returncode != 0:
        print(proc.stdout[-2000:]); sys.exit("Gowin build failed (see .build/opt/last_build.log).")
    r = parse_reports(build)
    rows = read_log()
    ref = best_gated(rows)
    if gate != "pass":
        verdict = "INVALID (gate " + gate + ")"
    elif ref is None:
        verdict = "FIRST"
    else:
        d = (r["logic"], r["registers"]), key(ref)
        verdict = "BETTER" if d[0] < d[1] else ("SAME" if d[0] == d[1] else "WORSE")
        verdict += f" vs best ({ref['label']}: {ref['logic']}/{ref['registers']})"
    LOG.parent.mkdir(exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": datetime.datetime.now().isoformat(timespec="seconds"), "label": a.label,
                    "logic": r["logic"], "lut": r["lut"], "alu": r["alu"], "ram16": r["ram16"],
                    "registers": r["registers"], "bsram": r["bsram"], "pnr_logic": r["pnr_logic"],
                    "gate": gate, "verdict": verdict, "src_hash": src_hash()})
    print_modules(r["modules"])
    print(f"\nLogic={r['logic']} (LUT {r['lut']}, ALU {r['alu']}, RAM16 {r['ram16']})  "
          f"Registers={r['registers']}  BSRAM={r['bsram']}  routed Logic={r['pnr_logic']}")
    print("VERDICT:", verdict)


def cmd_parse(a):
    r = parse_reports(a.reports)
    print_modules(r.pop("modules")) if r["modules"] else None
    print(json.dumps({k: v for k, v in r.items() if k != "modules"}, indent=2))


def cmd_compare(a):
    rows = read_log()
    if not rows:
        sys.exit("No log yet.")
    print(f"{'label':<36}{'Logic':>6}{'Reg':>6}{'BSRAM':>6}{'gate':>8}  verdict")
    for r in sorted(rows, key=lambda r: (r["gate"] != "pass",) + key(r)):
        print(f"{r['label'][:35]:<36}{r['logic']:>6}{r['registers']:>6}{r['bsram']:>6}{r['gate']:>8}  {r['verdict']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    for n, fn in (("freeze", cmd_freeze), ("restore", cmd_restore)):
        q = s.add_parser(n); q.add_argument("--name"); q.set_defaults(fn=fn)
    s.add_parser("gate").set_defaults(fn=cmd_gate)
    q = s.add_parser("measure")
    q.add_argument("--label", required=True)
    q.add_argument("--gw-sh")
    q.add_argument("--flow", default="all", choices=["syn", "pnr", "all"])
    q.add_argument("--skip-gate", action="store_true")
    q.add_argument("--reuse-project", action="store_true")
    q.set_defaults(fn=cmd_measure)
    q = s.add_parser("parse"); q.add_argument("--reports", required=True); q.set_defaults(fn=cmd_parse)
    s.add_parser("compare").set_defaults(fn=cmd_compare)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
