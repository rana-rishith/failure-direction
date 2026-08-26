"""Failure Direction — predicting which way speech enhancement breaks, before it runs."""

__version__ = "0.1.0"

from failure_direction.direction.index import DirectionResult, direction_index

__all__ = ["direction_index", "DirectionResult", "__version__"]
