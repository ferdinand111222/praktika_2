#!/bin/sh
case "$1" in
    install)
        python3 -m pip install -r requirements.txt ;;
    examples)
        python3 -m src.samples
        for f in examples/*.ogg; do
            if python3 src/tool.py "$f" > "${f%.ogg}.mp3"; then
                echo "Готово: $f -> ${f%.ogg}.mp3"
            else
                rm -f "${f%.ogg}.mp3"
            fi
        done ;;
    tool)
        if python3 src/tool.py "$2" > "${2%.ogg}.mp3"; then
            echo "Готово: ${2%.ogg}.mp3"
        else
            rm -f "${2%.ogg}.mp3"
        fi ;;
    server)
        python3 -m src.server ;;
    test)
        python3 -m coverage run -m unittest -v
        python3 -m coverage report ;;
    *)
        echo "Использование: ./run.sh install | examples | tool ФАЙЛ.ogg | server | test"
        exit 1 ;;
esac
