"""Progressive hiding of poem words for memorization practice."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PracticeLevel:
    level: int
    label: str
    icon: str
    hide_ratio: float


LEVELS = [
    PracticeLevel(0, "Унших", "👀", 0.0),
    PracticeLevel(1, "Бага нуух", "🙈", 0.3),
    PracticeLevel(2, "Их нуух", "🙉", 0.6),
    PracticeLevel(3, "Эхний үсэг", "🧠", 1.0),
]


@dataclass(frozen=True)
class MaskedWord:
    text: str
    hidden: bool

    @property
    def hint(self) -> str:
        return self.text[0]


def mask_lines(lines: list[str], level: int, seed: int = 0) -> list[list[MaskedWord]]:
    ratio = LEVELS[max(0, min(level, len(LEVELS) - 1))].hide_ratio
    rng = random.Random(f"{seed}:{level}")
    return [[MaskedWord(word, rng.random() < ratio) for word in line.split()] for line in lines]
