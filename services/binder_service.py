"""
binder_service.py
-----------------
Service layer that wraps a Binder implementation.

Responsibilities:
- Validate inputs coming from controllers.
- Translate controller requests into binder operations.
- Provide clear, typed API for controllers and tests.
- Wrap and normalize errors into BinderServiceError.

Standards applied:
- snake_case for functions/variables
- small functions (aim <= 30 lines)
- docstrings for public functions (what/inputs/outputs/side-effects)
- no hidden state: binder.current_user must be set explicitly by set_current_user
- logging used instead of prints
- TODOs and NOTES placed where further work is expected

# TODO: add pytest tests under /tests/test_binder_service.py
"""

from typing import Any, Callable, Dict, List, Optional
import logging

from binder import Binder


class BinderServiceError(Exception):
    """Raised when the BinderService cannot complete an operation."""


class BinderService:
    """
    Service wrapper around a Binder implementation.

    Args:
        binder_impl (Binder): Concrete binder implementation injected by the caller.
        logger (logging.Logger | None): Optional logger. If not provided a module logger will be used.

    Example:
        service = BinderService(my_binder_impl)
        user = service.create_user({"id": "u1", "name": "Alice"})
    """

    def __init__(self, binder_impl: Binder, logger: Optional[logging.Logger] = None):
        self._binder = binder_impl
        self._logger = logger or logging.getLogger(__name__)

    # ------- Helpers / Validators -------

    def _ensure_id(self, payload: Dict[str, Any], field: str) -> None:
        """
        Ensure payload contains a non-empty 'field'.

        Args:
            payload (Dict[str, Any]): incoming payload to validate.
            field (str): required field name.

        Raises:
            BinderServiceError: when validation fails.
        """
        if payload is None or field not in payload or payload[field] is None:
            raise BinderServiceError(f"Payload must include non-empty '{field}'")

    def _wrap_and_log(self, action_name: str, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute func and map any exception to BinderServiceError with logging.

        Args:
            action_name (str): descriptive action name for logs.
            func (Callable): function to execute.
            *args: positional args forwarded to func.
            **kwargs: keyword args forwarded to func.

        Returns:
            Any: result of func(*args, **kwargs)

        Raises:
            BinderServiceError: on failure (wraps original exception).
        """
        try:
            safe_kwargs = {
                k: ("REDACTED" if (isinstance(k, str) and k.lower().endswith("_token")) else v)
                for k, v in kwargs.items()
            }
            self._logger.debug(
                "binder_service: performing action %s with args=%s kwargs=%s",
                action_name,
                args,
                safe_kwargs,
            )
            return func(*args, **kwargs)
        except BinderServiceError:
            raise
        except Exception as exc:
            self._logger.exception("binder_service: error during %s", action_name)
            raise BinderServiceError(f"Error performing '{action_name}': {exc}") from exc

    # ------- Public API: User operations -------

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's record and set them as the current user in the binder.

        Args:
            user_id (str): target user id.

        Returns:
            Dict[str, Any]: the user record as returned by binder.read.

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        if user_id is None:
            raise BinderServiceError("user_id cannot be empty")

        user = self._wrap_and_log("get_user", self._binder.read, user_id)
        self.set_current_user(user_id=user_id)
        return user

    def create_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a user and set them as the current user in the binder.

        Args:
            user (Dict[str, Any]): user payload. MUST include 'id'.

        Returns:
            Dict[str, Any]: created user record (as returned by binder.create).

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        self._ensure_id(user, "id")
        created = self._wrap_and_log("create_user", self._binder.create, user)
        self.set_current_user(user["id"])
        return created

    def update_user(self, user_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user record and return the updated record.

        Args:
            user_id (str): id of the user to update.
            user (Dict[str, Any]): patch or full payload.

        Returns:
            Dict[str, Any]: updated user record (empty dict if binder returns None).

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        if user_id is None:
            raise BinderServiceError("user_id cannot be empty")
        if user is None:
            raise BinderServiceError("user payload cannot be empty")

        self._wrap_and_log("update_user", self._binder.update, user_id, user)
        updated = self._wrap_and_log("read_user_after_update", self._binder.read, user_id)
        if updated is None:
            self._logger.warning("update_user: user %s updated but read returned None", user_id)
            return {}
        return updated

    def set_current_user(self, user_id: str) -> None:
        """
        Set current user context on the binder.

        Args:
            user_id (str): non-empty user identifier.

        Side effects:
            - Mutates self._binder.current_user via binder contract.
        """
        if user_id is None:
            raise BinderServiceError("user_id cannot be empty")

        def _setter(uid: str) -> None:
            self._binder.current_user = uid

        self._wrap_and_log("set_current_user", _setter, user_id)

    # ------- Public API: Client / Patient operations -------

    def create_client(self, client: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a client (patient) under the current user context.

        Args:
            client (Dict[str, Any]): client payload.

        Returns:
            Dict[str, Any]: created client record.

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        if client is None:
            raise BinderServiceError("client payload cannot be empty")
        return self._wrap_and_log("create_client", self._binder.create_client, client)

    def read_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a client by id.

        Args:
            client_id (str): client identifier.

        Returns:
            Optional[Dict[str, Any]]: client dict if found, else None.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        return self._wrap_and_log("read_client", self._binder.read_client, client_id)

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a client's fields and return the updated client.

        Args:
            client_id (str): id of the client to update.
            patch (Dict[str, Any]): partial update document (non-empty).

        Returns:
            Dict[str, Any]: updated client document (empty dict if binder read returns None).
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if patch is None:
            raise BinderServiceError("patch cannot be empty")

        self._wrap_and_log("update_client", self._binder.update_client, client_id, patch)
        updated = self._wrap_and_log("read_client_after_update", self._binder.read_client, client_id)
        if updated is None:
            self._logger.warning("update_client: client %s updated but read returned None", client_id)
            return {}
        return updated

    def delete_client(self, client_id: str) -> None:
        """
        Delete a client.

        Args:
            client_id (str): id of the client to remove.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        self._wrap_and_log("delete_client", self._binder.delete_client, client_id)

    def search_client(self, query: str) -> List[Dict[str, Any]]:
        """
        Unified search facade used by routes. Delegates to binder.search_clients.

        Args:
            query (str): search string.

        Returns:
            List[Dict[str, Any]]: matching client records (possibly empty list).
        """
        if query is None:
            return []
        return self._wrap_and_log("search_client", self._binder.search_clients, query)

    # --- appointments ---

    def get_appointments(self, date: str) -> List[Dict[str, Any]]:
        """
        Retrieve appointments for a date.

        Args:
            date (str): date in binder-expected format.

        Returns:
            List[Dict[str, Any]]: appointment list (may be empty).
        """
        if date is None:
            raise BinderServiceError("date cannot be empty")
        return self._wrap_and_log("get_appointments", self._binder.get_appointments, date)

    def save_appointments(self, date: str, appointments: List[Dict[str, Any]]) -> None:
        """
        Save appointments for a date.

        Args:
            date (str): target date.
            appointments (List[Dict[str, Any]]): appointments payload.
        """
        if date is None:
            raise BinderServiceError("date cannot be empty")
        if appointments is None:
            raise BinderServiceError("appointments cannot be empty")
        self._wrap_and_log("save_appointments", self._binder.save_appointments, date, appointments)

    def lock_appointment(self, date: str, no: str) -> bool:
        """
        Acquire a lock for a specific appointment number on a date.

        Args:
            date (str): target date.
            no (str): appointment number (string).

        Returns:
            bool: True if lock acquired, False otherwise.
        """
        if date is None or no is None:
            raise BinderServiceError("date and no are required")
        return self._wrap_and_log("lock_appointment", self._binder.lock_appointment, date, no)

    # --- permission codes ---

    def rotate_permission_code(self, domain: str, user_id: str, plan: str = "sec") -> str:
        """
        Rotate or create a permission code for a user.

        Args:
            domain (str): Domain name (e.g. 'drs').
            user_id (str): Code owner.
            plan (str): Permission plan.

        Returns:
            str: Newly generated code.
        """
        if domain is None:
            raise BinderServiceError("domain cannot be empty")
        if user_id is None:
            raise BinderServiceError("user_id cannot be empty")

        return self._wrap_and_log(
            "rotate_permission_code",
            self._binder.rotate_permission_code,
            domain,
            user_id,
            plan,
        )

    def validate_permission_code(self, domain: str, code: str) -> Optional[Dict[str, Any]]:
        """
        Validate a permission code and return ownership metadata.

        Args:
            domain (str): domain name.
            code (str): code to validate.

        Returns:
            Optional[Dict[str, Any]]: metadata if valid, else None.
        """
        if domain is None:
            raise BinderServiceError("domain cannot be empty")
        if code is None:
            raise BinderServiceError("code cannot be empty")

        return self._wrap_and_log(
            "validate_permission_code",
            self._binder.validate_permission_code,
            domain=domain,
            code=code,
        )

    def consume_permission_code(self, domain: str, owner_user_id: str) -> None:
        """
        Increment usage counter for a permission code.

        Args:
            domain (str): domain name.
            owner_user_id (str): owner id.
        """
        if domain is None or owner_user_id is None:
            raise BinderServiceError("domain and owner_user_id are required")

        self._wrap_and_log(
            "consume_permission_code",
            self._binder.consume_permission_code,
            domain,
            owner_user_id,
        )

    # ------- Public API: Interactions (visits/transactions) -------

    def update_interaction(self, client_id: str, interaction_no: int, patch: List[Any]) -> Dict[str, Any]:
        """
        Update a single interaction (visit/transaction) and return the client's up-to-date record.

        Args:
            client_id (str): id of the client to update.
            interaction_no (int): index/id of the interaction to update.
            patch (List[Any]): partial update document (non-empty).

        Returns:
            Dict[str, Any]: updated client document (empty dict if read returns None).
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if interaction_no is None:
            raise BinderServiceError("interaction_no cannot be empty")
        if patch is None:
            raise BinderServiceError("patch cannot be empty")

        self._wrap_and_log("update_interaction", self._binder.update_interaction, client_id, interaction_no, patch)
        updated = self._wrap_and_log("read_client_after_interaction_update", self._binder.read_client, client_id)
        if updated is None:
            self._logger.warning(
                "update_interaction: client %s updated but read returned None", client_id
            )
            return {}
        return updated

    def delete_interaction(self, client_id: str, interaction_no: int) -> None:
        """
        Delete an interaction for a client.

        Args:
            client_id (str): id of the client.
            interaction_no (int): id/index of the interaction.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if interaction_no is None:
            raise BinderServiceError("interaction_no cannot be empty")
        self._wrap_and_log("delete_interaction", self._binder.delete_interaction, client_id, interaction_no)

    def create_interaction(self, client_id: str, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an interaction (visit, transaction) for a given client.

        Args:
            client_id (str): target client id.
            interaction (Dict[str, Any]): interaction payload; must be non-empty.

        Returns:
            Dict[str, Any]: created interaction record.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if interaction is None:
            raise BinderServiceError("interaction payload cannot be empty")
        return self._wrap_and_log("create_interaction", self._binder.create_interaction, client_id, interaction)

    def list_interactions(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List interactions for a client.

        Args:
            client_id (str): client id.

        Returns:
            List[Dict[str, Any]]: list of interactions (empty list if none).
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        return self._wrap_and_log("list_interactions", self._binder.list_interactions, client_id)

    # --------------------
    # Employees CRUD
    # --------------------

    def create_employee(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an employee under the current user context.

        Args:
            data (Dict[str, Any]): employee payload.

        Returns:
            Dict[str, Any]: created employee record.
        """
        if data is None:
            raise BinderServiceError("employee payload cannot be empty")
        return self._wrap_and_log("create_employee", self._binder.create_employee, data)

    def read_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Read an employee by id.

        Args:
            employee_id (str): employee id.

        Returns:
            Optional[Dict[str, Any]]: employee record or None.
        """
        if employee_id is None:
            raise BinderServiceError("employee_id cannot be empty")
        return self._wrap_and_log("read_employee", self._binder.read_employee, employee_id)

    def update_employee(self, emp_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an employee and return the up-to-date record.

        Args:
            emp_id (str): employee id.
            patch (Dict[str, Any]): patch.

        Returns:
            Dict[str, Any]: updated employee record (empty dict if read returns None).
        """
        if emp_id is None:
            raise BinderServiceError("emp_id cannot be empty")
        if patch is None:
            raise BinderServiceError("patch cannot be empty")

        self._wrap_and_log("update_employee", self._binder.update_employee, emp_id, patch)
        updated = self._wrap_and_log("read_employee_after_update", self._binder.read_employee, emp_id)
        if updated is None:
            self._logger.warning("update_employee: employee %s updated but read returned None", emp_id)
            return {}
        return updated

    def delete_employee(self, emp_id: str) -> None:
        """
        Delete an employee.

        Args:
            emp_id (str): employee id.
        """
        if emp_id is None:
            raise BinderServiceError("emp_id cannot be empty")
        self._wrap_and_log("delete_employee", self._binder.delete_employee, emp_id)

    def list_employees(self) -> List[Dict[str, Any]]:
        """
        List employees for current user.

        Returns:
            List[Dict[str, Any]]: employee list.
        """
        # Prefer binder-provided list_employees if available, else fall back to adapter.
        if hasattr(self._binder, "list_employees"):
            return self._wrap_and_log("list_employees", self._binder.list_employees)
        # fallback: use adapter.list_children (binder must expose domain/current_user)
        return self._wrap_and_log(
            "list_employees_fallback",
            self._binder.adapter.list_children,
            getattr(self._binder, "domain", None),
            getattr(self._binder, "current_user", None),
            "employees",
        )

    # --------------------
    # Products CRUD
    # --------------------

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a product under the current user context.

        Args:
            data (Dict[str, Any]): product payload.

        Returns:
            Dict[str, Any]: created product record.
        """
        if data is None:
            raise BinderServiceError("product payload cannot be empty")

        # binder mixin defines create_products (plural); call it but keep service API singular.
        if hasattr(self._binder, "create_product"):
            return self._wrap_and_log("create_product", self._binder.create_product, data)
        return self._wrap_and_log("create_products", self._binder.create_products, data)

    def read_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a product by id.

        Args:
            product_id (str): product id.

        Returns:
            Optional[Dict[str, Any]]: product record or None.
        """
        if product_id is None:
            raise BinderServiceError("product_id cannot be empty")
        return self._wrap_and_log("read_product", self._binder.read_product, product_id)

    def update_product(self, prod_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a product and return the up-to-date record.

        Args:
            prod_id (str): product id.
            patch (Dict[str, Any]): patch.

        Returns:
            Dict[str, Any]: updated product record (empty dict if read returns None).
        """
        if prod_id is None:
            raise BinderServiceError("prod_id cannot be empty")
        if patch is None:
            raise BinderServiceError("patch cannot be empty")

        self._wrap_and_log("update_product", self._binder.update_product, prod_id, patch)
        updated = self._wrap_and_log("read_product_after_update", self._binder.read_product, prod_id)
        if updated is None:
            self._logger.warning("update_product: product %s updated but read returned None", prod_id)
            return {}
        return updated

    def delete_product(self, prod_id: str) -> None:
        """
        Delete a product.

        Args:
            prod_id (str): product id.
        """
        if prod_id is None:
            raise BinderServiceError("prod_id cannot be empty")
        self._wrap_and_log("delete_product", self._binder.delete_product, prod_id)

    def list_products(self) -> List[Dict[str, Any]]:
        """
        List products for current user.

        Returns:
            List[Dict[str, Any]]: product list.
        """
        if hasattr(self._binder, "list_products"):
            return self._wrap_and_log("list_products", self._binder.list_products)
        return self._wrap_and_log(
            "list_products_fallback",
            self._binder.adapter.list_children,
            getattr(self._binder, "domain", None),
            getattr(self._binder, "current_user", None),
            "products",
        )

    # --------------------
    # Services CRUD
    # --------------------

    def create_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a service (business offering) under current user.

        Args:
            data (Dict[str, Any]): service payload.

        Returns:
            Dict[str, Any]: created service record.
        """
        if data is None:
            raise BinderServiceError("service payload cannot be empty")
        return self._wrap_and_log("create_service", self._binder.create_service, data)

    def read_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a service by id.

        Args:
            service_id (str): service id.

        Returns:
            Optional[Dict[str, Any]]: service record or None.
        """
        if service_id is None:
            raise BinderServiceError("service_id cannot be empty")
        return self._wrap_and_log("read_service", self._binder.read_service, service_id)

    def update_service(self, svc_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a service and return the up-to-date record.

        Args:
            svc_id (str): service id.
            patch (Dict[str, Any]): patch.

        Returns:
            Dict[str, Any]: updated service record (empty dict if read returns None).
        """
        if svc_id is None:
            raise BinderServiceError("svc_id cannot be empty")
        if patch is None:
            raise BinderServiceError("patch cannot be empty")

        self._wrap_and_log("update_service", self._binder.update_service, svc_id, patch)
        updated = self._wrap_and_log("read_service_after_update", self._binder.read_service, svc_id)
        if updated is None:
            self._logger.warning("update_service: service %s updated but read returned None", svc_id)
            return {}
        return updated

    def delete_service(self, svc_id: str) -> None:
        """
        Delete a service.

        Args:
            svc_id (str): service id.
        """
        if svc_id is None:
            raise BinderServiceError("svc_id cannot be empty")
        self._wrap_and_log("delete_service", self._binder.delete_service, svc_id)

    def list_services(self) -> List[Dict[str, Any]]:
        """
        List services for current user.

        Returns:
            List[Dict[str, Any]]: services list.
        """
        if hasattr(self._binder, "list_services"):
            return self._wrap_and_log("list_services", self._binder.list_services)
        return self._wrap_and_log(
            "list_services_fallback",
            self._binder.adapter.list_children,
            getattr(self._binder, "domain", None),
            getattr(self._binder, "current_user", None),
            "services",
        )

    # --------------------
    # Transactions (nested) CRUD
    # --------------------

    def create_transaction(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a transaction nested under a client.

        Args:
            client_id (str): target client id.
            data (Dict[str, Any]): transaction payload.

        Returns:
            Dict[str, Any]: created transaction record.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if data is None:
            raise BinderServiceError("transaction payload cannot be empty")
        return self._wrap_and_log("create_transaction", self._binder.create_transaction, client_id, data)

    def list_transactions(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List transactions for a client.

        Args:
            client_id (str): client id.

        Returns:
            List[Dict[str, Any]]: transaction list.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        return self._wrap_and_log("list_transactions", self._binder.list_transactions, client_id)

    def update_transaction(self, client_id: str, txn_no: int, patch: List[Any]) -> Dict[str, Any]:
        """
        Update a transaction and return the client's up-to-date record.

        This method prefers binder.update_transaction if available; otherwise it falls back
        to calling the adapter.update_nested contract directly.

        Args:
            client_id (str): client id.
            txn_no (int): transaction index/id.
            patch (List[Any]): update patch.

        Returns:
            Dict[str, Any]: updated client document (empty dict if read returns None).
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if txn_no is None:
            raise BinderServiceError("txn_no cannot be empty")
        if patch is None:
            raise BinderServiceError("patch cannot be empty")

        if hasattr(self._binder, "update_transaction"):
            self._wrap_and_log("update_transaction", self._binder.update_transaction, client_id, txn_no, patch)
        else:
            # Fallback to adapter: update_nested(domain, user, "clients", client_id, "transactions", txn_no, patch)
            self._wrap_and_log(
                "update_transaction_fallback",
                self._binder.adapter.update_nested,
                getattr(self._binder, "domain", None),
                getattr(self._binder, "current_user", None),
                "clients",
                client_id,
                "transactions",
                txn_no,
                patch,
            )

        updated = self._wrap_and_log("read_client_after_txn_update", self._binder.read_client, client_id)
        if updated is None:
            self._logger.warning("update_transaction: client %s updated but read returned None", client_id)
            return {}
        return updated

    def delete_transaction(self, client_id: str, txn_no: int) -> None:
        """
        Delete a nested transaction for a client.

        Args:
            client_id (str): client id.
            txn_no (int): transaction index/id.

        Side effects:
            - Calls binder.delete_transaction or falls back to adapter.delete_nested.
        """
        if client_id is None:
            raise BinderServiceError("client_id cannot be empty")
        if txn_no is None:
            raise BinderServiceError("txn_no cannot be empty")

        if hasattr(self._binder, "delete_transaction"):
            self._wrap_and_log("delete_transaction", self._binder.delete_transaction, client_id, txn_no)
        else:
            self._wrap_and_log(
                "delete_transaction_fallback",
                self._binder.adapter.delete_nested,
                getattr(self._binder, "domain", None),
                getattr(self._binder, "current_user", None),
                "clients",
                client_id,
                "transactions",
                txn_no,
            )


if __name__ == "__main__":
    # NOTE: demo only. In production, instantiate BinderService from application bootstrap.
    logging.basicConfig(level=logging.DEBUG)
    from binder import BinderBusiness, FirebaseCrudAdapter

    adapter = FirebaseCrudAdapter("test")
    demo_binder = BinderBusiness(adapter)
    service = BinderService(demo_binder)

    # minimal smoke demo that tolerates binder-assigned ids
    user = {"id": "u1", "name": "Alice"}
    created_user = service.create_user(user)
    print("create_user ->", created_user)

    client = {"name": "Bob"}
    created_client = service.create_client(client)
    print("create_client ->", created_client)

    # interactions / transactions demo
    interaction = {"type": "visit", "notes": "Initial checkup"}
    created_interaction = service.create_interaction(created_client.get("id", "0"), interaction)
    print("create_interaction ->", created_interaction)

    txn = {"amount": 50, "notes": "Payment"}
    created_txn = service.create_transaction(created_client.get("id", "0"), txn)
    print("create_transaction ->", created_txn)

    print("list_transactions ->", service.list_transactions(created_client.get("id", "0")))
