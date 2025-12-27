"""
gde_registry.py
---------------
Central registry for GDE constraints and actions.

Why this exists:
- Allows adding new constraints/actions without touching engine logic
- Keeps the system open for extension, closed for modification
"""

CONSTRAINTS = []
ACTIONS = []


def register_constraint(constraint):
    """
    Register a constraint instance.

    Args:
        constraint (object): Constraint instance
    """
    CONSTRAINTS.append(constraint)


def register_action(action):
    """
    Register an action instance.

    Args:
        action (object): Action instance
    """
    ACTIONS.append(action)


def get_constraints():
    """Return all registered constraints."""
    return CONSTRAINTS


def get_actions_for_constraint(constraint_name: str) -> list:
    """
    Return actions linked to a specific constraint.

    Args:
        constraint_name (str): Name of the constraint

    Returns:
        list: Matching action instances
    """
    return [a for a in ACTIONS if a.constraint_name == constraint_name]
