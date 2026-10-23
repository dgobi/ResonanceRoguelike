"""Full production-main D gate, including B1/B2/B3/C regressions."""
from verify_b3 import main
if __name__ == '__main__':
    raise SystemExit(main(include_d=True))
