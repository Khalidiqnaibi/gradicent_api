"""
binder_service.py
-----------------
Service layer that wraps a Binder implementation.

Responsibilities:
- Validate inputs coming from controllers.
- Translate controller requests into binder operations.
- Provide clear, typed API for controllers and tests.
- Wrap and normalize errors into BinderServiceError.

Notes:
- This module follows company code standards:
  * snake_case for functions/variables
  * small functions (aim <= 30 lines)
  * docstrings for every public function explaining what/inputs/outputs/side-effects
  * no hidden state (binder.current_user is always set explicitly)
  * use logging instead of prints
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
            # redact tokens in kwargs for logging
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
            # let BinderServiceError bubble through unchanged
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
        # set current user to avoid hidden state surprises in downstream code
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
        # set current user to avoid hidden state surprises in downstream code
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

        Note:
            Some binder implementations auto-assign an 'id' for clients. Do not rely
            on the presence of 'id' in the input; the binder may mutate/assign it.

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

        Raises:
            BinderServiceError: on validation failure.
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

        Raises:
            BinderServiceError: on validation or binder failure.
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

        Side effects:
            - Calls binder.delete_client.
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

        Side effects:
            - Calls binder.save_appointments.
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

        Side effects:
            - Calls binder.consume_permission_code.
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

        Side effects:
            - Calls binder.delete_interaction.
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


if __name__ == "__main__":
    # NOTE: demo only. In production, instantiate BinderService from application bootstrap.
    logging.basicConfig(level=logging.DEBUG)
    from binder import BinderBusiness, FirebaseCrudAdapter

    adapter = FirebaseCrudAdapter("test")
    demo_binder = BinderBusiness(adapter)
    service = BinderService(demo_binder)

    # create user
    user = {"id": "u1", "name": "Alice"}
    created_user = service.create_user(user)
    print("create_user ->", created_user)

    # create client
    client = {"name": "Bob"}  # binder may assign id
    created_client = service.create_client(client)
    print("create_client ->", created_client)

    # add interaction
    interaction = {"type": "visit", "notes": "Initial checkup"}
    created_interaction = service.create_interaction(created_client.get("id", "0"), interaction)
    print("create_interaction ->", created_interaction)

    # list interactions
    print("list_interactions ->", service.list_interactions(created_client.get("id", "0")))

    # update client
    updated_client = service.update_client(created_client.get("id", "0"), {"name": "Bobby"})
    print("update_client ->", updated_client)

    # read client
    print("read_client ->", service.read_client(created_client.get("id", "0")))

    # delete client
    service.delete_client(created_client.get("id", "0"))
    print("read_client after delete ->", service.read_client(created_client.get("id", "0")))
