"""Manual kilominx solver sweep (heavier than the fast-suite fuzz).

Run: python3 build/diag_kilo.py [N] [start_seed]
Prints "<solved>/<N> solved" and exits non-zero if any seed fails.
"""
import sys
sys.path.insert(0, '/home/kurtt/megaminx')
from minx import puzzle as P
from minx.method_kilo import KiloSolver, scramble
from minx.solver import MethodError


def main(n=200, start=0):
    fails = 0
    for seed in range(start, start + n):
        m = P.KILOMINX.minx()
        scramble(m, n=40, seed=seed)
        try:
            s = KiloSolver(m, white=0)
            s.solve()
            if not s.m.is_solved():
                print(f"seed {seed}: finished unsolved")
                fails += 1
        except MethodError as e:
            print(f"seed {seed}: {e}")
            fails += 1
    print(f"{n - fails}/{n} solved")
    return fails


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    sys.exit(1 if main(n, start) else 0)
