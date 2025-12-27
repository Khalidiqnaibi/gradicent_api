"""
gde_service.py
--------------
Service layer for GDE.
"""

from gde import GDEngine


def analyze_business_decisions(binder) -> dict:
    """
    Run decision engine for a business.

    Args:
        binder: Binder instance

    Returns:
        dict: GDE output
    """
    engine = GDEngine()
    return engine.analyze_business(binder)
