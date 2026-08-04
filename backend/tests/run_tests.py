import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.test_derivations as td

def main():
    test_funcs = [
        obj for name, obj in vars(td).items()
        if name.startswith("test_") and callable(obj)
    ]

    print(f"Running {len(test_funcs)} derivation & resolution unit tests...\n")
    passed = 0
    failed = 0

    for func in test_funcs:
        try:
            func()
            print(f"  [PASS] {func.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {func.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED out of {len(test_funcs)} tests.")
    print("=" * 50)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
