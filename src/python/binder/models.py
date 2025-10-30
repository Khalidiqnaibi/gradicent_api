"""
Models
----------
Dataclasses representing business entities. Keeps structure consistent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


def now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class Client:
    id: str
    name: str
    metadata: Dict[str, any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    interactions: List[Dict] = field(default_factory=list)
    transactions: List[Dict] = field(default_factory=list)


@dataclass
class Employee:
    id: str
    name: str
    role: str
    metadata: Dict[str, any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)


@dataclass
class Product:
    id: str
    name: str
    price: float
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class Service:
    id: str
    name: str
    hourly_rate: float
    metadata: Dict[str, any] = field(default_factory=dict)
