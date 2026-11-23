"""Этап 1. Утилита командной строки.

Читает файл с числами (через пробел или с новой строки) и печатает
их количество, сумму, минимум, максимум и среднее значение.

Запуск:
    python src/tool.py examples/1.txt
"""
import argparse
import sys


def to_number(word):
    """Превратить слово в число или сообщить, что это не число."""
    try:
        return float(word)
    except ValueError:
        raise ValueError(f"'{word}' - не число") from None


def solve(text):
    """Посчитать статистику по числам из текста и вернуть строку."""
    numbers = [to_number(word) for word in text.split()]
    if not numbers:
        raise ValueError("в файле нет чисел")
    total = sum(numbers)
    mean = total / len(numbers)
    return (f"количество: {len(numbers)}, сумма: {total:g}, "
            f"минимум: {min(numbers):g}, максимум: {max(numbers):g}, "
            f"среднее: {mean:g}")


def main():
    """Прочитать файл из командной строки и вывести результат."""
    parser = argparse.ArgumentParser(description="Статистика по числам")
    parser.add_argument("file", help="путь к файлу с числами")
    args = parser.parse_args()
    try:
        with open(args.file, encoding="utf-8") as file:
            print(solve(file.read()))
    except (OSError, ValueError) as error:
        sys.exit(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
