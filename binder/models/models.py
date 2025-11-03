"""
Models For Binder 
---------------------
Uniform dataclasses for users, clients, employees, products, services,
interactions and transactions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional


def now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class User:
    '''
    user dataclass

    expects:
        id: str
        name: str
        email: Optional[str] 
        created_at: str 
        metadata: Dict[str, Any] 
        clients: List[Dict[str, Any]] 
        employees: List[Dict[str, Any]]
        products: List[Dict[str, Any]] 
        services: List[Dict[str, Any]]
    '''
    id: str
    name: str
    email: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)
    clients: List[Dict[str, Any]] = field(default_factory=list)
    employees: List[Dict[str, Any]] = field(default_factory=list)
    products: List[Dict[str, Any]] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Client:
    id: str
    name: str
    contact: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)
    interactions: List[Dict[str, Any]] = field(default_factory=list)
    transactions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Employee:
    id: str
    name: str
    role: str
    salary: float = 0.0
    created_at: str = field(default_factory=now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Service:
    id: str
    name: str
    hourly_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Interaction:
    id: str
    type: str
    note: Optional[str] = ""
    timestamp: str = field(default_factory=now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Transaction:
    id: str
    amount: float
    method: str
    timestamp: str = field(default_factory=now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
