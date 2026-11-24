"""Тесты утилиты командной строки (этап 1) на основе hypothesis."""
import io
import os
import tempfile
import unittest

import numpy
import soundfile
from hypothesis import given, settings, strategies as st

from src.samples import tone
from src.tool import convert

RATES = st.sampled_from([8000, 16000, 22050, 44100, 48000])
FREQUENCIES = st.lists(st.integers(100, 2000), max_size=3)
SECONDS = st.sampled_from([0.1, 0.5, 1.0])
LETTERS = st.text(alphabet="абвгдежзabcdefgh ", min_size=1, max_size=20)


def convert_text(text, name):
    """Записать текст в файл name во временной папке и преобразовать."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return convert(path)


class TestTool(unittest.TestCase):
    """Проверки функции convert на случайных звуках."""

    @settings(max_examples=30, deadline=None)
    @given(FREQUENCIES, SECONDS, RATES, st.booleans())
    def test_ogg_becomes_mp3(self, frequencies, seconds, rate, stereo):
        """Из OGG получается MP3 с той же частотой, каналами и длиной."""
        sound = tone(frequencies, seconds, rate)
        if stereo:
            sound = numpy.column_stack([sound, sound])
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "in.ogg")
            soundfile.write(path, sound, rate, format="OGG")
            info = soundfile.info(io.BytesIO(convert(path)))
        self.assertEqual(info.format, "MP3")
        self.assertEqual(info.samplerate, rate)
        self.assertEqual(info.channels, sound.ndim)
        self.assertAlmostEqual(info.duration, seconds, places=2)

    @given(st.sampled_from(["нет.ogg", "missing.ogg"]))
    def test_missing_file(self, name):
        """Несуществующий файл - это ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                convert(os.path.join(folder, name))

    def test_not_ogg(self):
        """Звук в другом формате (WAV) - это ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "in.wav")
            soundfile.write(path, tone([440], 0.1), 8000)
            with self.assertRaises(ValueError):
                convert(path)

    @given(LETTERS)
    def test_broken_file(self, text):
        """Текст вместо звука - это ошибка чтения."""
        with self.assertRaises(ValueError):
            convert_text(text, "bad.ogg")
