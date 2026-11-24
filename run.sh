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
    server)
        python3 -m src.server ;;
    test)
        python3 -m coverage run -m unittest -v
        python3 -m coverage report ;;
    *)
        echo "Использование: ./run.sh install | tool ФАЙЛ | examples | server | test"
        exit 1 ;;
esac
