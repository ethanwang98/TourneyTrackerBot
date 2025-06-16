from abc import ABC, abstractmethod


class BaseTracker(ABC):

    @abstractmethod
    async def check_for_updates(self):
        pass