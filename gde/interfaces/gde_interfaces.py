from abc import ABC, abstractmethod

class IConstraint(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def required_metrics(self) -> list[str]:
        pass

    @abstractmethod
    def score(self, metrics: dict) -> float:
        """
        Returns urgency score (0-10)
        """
        pass


class IAction(ABC):
    @property
    @abstractmethod
    def constraint_name(self) -> str:
        pass

    @abstractmethod
    def runbook(self) -> dict:
        """
        Returns step-by-step actions
        """
        pass
