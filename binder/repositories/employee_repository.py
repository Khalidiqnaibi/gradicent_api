"""
employee_repository.py
----------------------
Repository for employee records.
"""

from binder import Employee, BaseRepository


class EmployeeRepository(BaseRepository):
    def __init__(self, adapter):
        super().__init__(adapter, "employees", Employee)

    def get_by_role(self, role: str):
        return self.list(filters={"role": role})
