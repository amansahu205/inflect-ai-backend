"""Abstract base for Inflect agents."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """All agents accept a single dict payload and return a dict result."""

    name: str = "base"

    @abstractmethod
    async def run(self, input: dict) -> dict:
        pass
