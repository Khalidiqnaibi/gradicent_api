"""
employee_repository.py
----------------------
Repository for employee records.
"""
from ..models.models import Employee  
from ..interfaces.base_repository import BaseRepository


class EmployeeRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "employees", Employee)

    def get_by_role(self, role: str):
        return self.list(filters={"role": role})
