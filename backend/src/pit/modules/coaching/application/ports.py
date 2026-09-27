"""What the coach needs from outside the module."""

from typing import Protocol

from pit.modules.challenges.domain.challenge import Challenge
from pit.modules.challenges.domain.roadmap import Roadmap
from pit.modules.challenges.domain.schedule import TaskSpec


class ChallengeTexts(Protocol):
    """A challenge's texts in the reader's language. The catalog is translated outside this
    module; user-made challenges are already written in their author's language."""

    def title(self, challenge: Challenge, locale: str) -> str: ...

    def roadmap(self, challenge: Challenge, locale: str) -> Roadmap | None: ...

    def task_title(self, challenge: Challenge, task: TaskSpec, locale: str) -> str: ...


class OwnTexts:
    """No translations: every challenge speaks the language it was written in."""

    def title(self, challenge: Challenge, locale: str) -> str:
        return challenge.title

    def roadmap(self, challenge: Challenge, locale: str) -> Roadmap | None:
        return challenge.roadmap

    def task_title(self, challenge: Challenge, task: TaskSpec, locale: str) -> str:
        return task.title
