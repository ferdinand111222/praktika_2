"""Этап 1. Утилита командной строки: преобразование OGG в MP3.

Читает аудиофайл в формате OGG и пишет тот же звук в формате MP3
в стандартный вывод, поэтому вывод нужно перенаправить в файл.

Запуск (в cmd):
    python src/tool.py examples/1.ogg > examples/1.mp3
"""
import argparse
import io
import os
import sys

import soundfile


def convert(path):
    """Прочитать OGG-файл и вернуть содержимое MP3 в виде байтов."""
    if not os.path.isfile(path):
        raise ValueError(f"файл не найден: {path}")
    try:
        info = soundfile.info(path)
    except RuntimeError:
        raise ValueError(f"файл повреждён или это не звук: {path}") from None
    if info.format != "OGG":
        raise ValueError(f"файл не в формате OGG: {path}")
    data, rate = soundfile.read(path)
    buffer = io.BytesIO()
    soundfile.write(buffer, data, rate, format="MP3")
    return buffer.getvalue()


def main():
    """Преобразовать файл из командной строки и вывести MP3."""
    parser = argparse.ArgumentParser(description="Преобразование OGG в MP3")
    parser.add_argument("file", help="путь к файлу OGG")
    args = parser.parse_args()
    if sys.stdout.isatty():
        sys.exit("Ошибка: перенаправьте вывод в файл, например > out.mp3")
    try:
        mp3 = convert(args.file)
    except (RuntimeError, ValueError) as error:
        sys.exit(f"Ошибка: {error}")
    sys.stdout.buffer.write(mp3)


if __name__ == "__main__":
    main()
