import sys

# Python version check
if sys.version_info < (3, 11) or sys.version_info >= (3, 12):
    print("This project requires Python 3.11")
    sys.exit(1)

from .app import main

if __name__ == "__main__":
    main()
