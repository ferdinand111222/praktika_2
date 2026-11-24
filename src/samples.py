"""Создание примеров входных данных: пяти аудиофайлов OGG.

Двоичные аудиофайлы не хранятся в репозитории, поэтому примеры
создаются этим модулем (из корня проекта):
    python -m src.samples
"""
import os

import numpy
import soundfile

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")
RATE = 44100
VOLUME = 0.3


def tone(frequencies, seconds, rate=RATE):
    """Сумма синусоид с частотами frequencies (Гц) длиной seconds секунд."""
    time = numpy.arange(int(seconds * rate)) / rate
    wave = numpy.zeros(len(time))
    for frequency in frequencies:
        wave += numpy.sin(2 * numpy.pi * frequency * time)
    return VOLUME * wave / max(len(frequencies), 1)


def samples():
    """Пять примеров: {имя файла: (звук, частота дискретизации)}."""
    stereo = numpy.column_stack([tone([440], 1.5), tone([660], 1.5)])
    return {
        "1.ogg": (tone([440], 1), RATE),
        "2.ogg": (tone([262, 330, 392], 2), RATE),
        "3.ogg": (stereo, RATE),
        "4.ogg": (tone([300], 1, 8000), 8000),
        "5.ogg": (tone([], 0.5), RATE),
    }


def make_samples(folder):
    """Создать в папке folder пять примеров OGG и битый файл error.ogg."""
    os.makedirs(folder, exist_ok=True)
    for name, (sound, rate) in samples().items():
        soundfile.write(os.path.join(folder, name), sound, rate,
                        format="OGG", subtype="VORBIS")
    with open(os.path.join(folder, "error.ogg"), "w",
              encoding="utf-8") as file:
        file.write("это текст, а не звук")


if __name__ == "__main__":
    make_samples(EXAMPLES)
