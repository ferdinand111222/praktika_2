#!/bin/sh
case "$1" in
    install)
        python3 -m pip install -r requirements.txt ;;
    tool)
        python3 src/tool.py "$2" ;;
    examples)
        for f in examples/*.txt; do
            echo "=== $f"
            python3 src/tool.py "$f"
        done ;;
    test)
        python3 -m unittest -v ;;
    *)
        echo "Usage: ./run.sh install | tool FILE | examples | test"
        exit 1 ;;
esac
