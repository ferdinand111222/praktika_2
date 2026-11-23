"""Тесты утилиты командной строки (этап 1) на основе hypothesis."""
import unittest

from hypothesis import given, strategies as st

from src.tool import solve

NUMBERS = st.lists(st.integers(-1000, 1000), min_size=1)
NOT_NUMBERS = st.sampled_from(["abc", "1,5", "x2"])


class TestTool(unittest.TestCase):
    """Проверки функции solve на случайных списках чисел."""

    @given(NUMBERS)
    def test_count_and_sum(self, numbers):
        """Количество и сумма совпадают с посчитанными в Python."""
        result = solve(" ".join(map(str, numbers)))
        self.assertIn(f"количество: {len(numbers)},", result)
        self.assertIn(f"сумма: {sum(numbers):g},", result)
        self.assertIn(f"минимум: {min(numbers):g},", result)
        self.assertIn(f"максимум: {max(numbers):g},", result)

    @given(st.text(alphabet=" \n"))
    def test_no_numbers(self, text):
        """Файл без чисел - это ошибка."""
        with self.assertRaises(ValueError):
            solve(text)

    @given(NUMBERS, NOT_NUMBERS)
    def test_not_a_number(self, numbers, word):
        """Слово, которое не является числом, - это ошибка."""
        text = " ".join(map(str, numbers)) + " " + word
        with self.assertRaises(ValueError):
            solve(text)
