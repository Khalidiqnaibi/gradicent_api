"""
binder_service.py
-----------------
Service layer that wraps a Binder implementation.

Responsibilities:
- Validate inputs coming from controllers.
- Translate controller requests into binder operations.
- Provide clear, typed API for controllers and tests.
- Wrap and normalize errors into BinderServiceError.

Design constraints:
- No hidden state: this service does not keep user-specific state; it delegates to
  the binder implementation which may be stateless or stateful depending on your choice.
- Each public method is small (aim <= 30 lines).
- No external dependencies (optional pydantic usage should be added separately).
"""

from typing import Any, Dict, List, Optional, Protocol
import logging
from binder import Binder

class BinderServiceError(Exception):
    """Raised when the BinderService cannot complete an operation."""
    pass


class BinderService:
    """
    Service wrapper around a Binder implementation.

    Args:
        binder_impl (BinderInterface): Concrete binder implementation injected by the caller.
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
        Ensure payload contains non-empty 'field'.

        Side effects:
            - Raises BinderServiceError on validation failure.
        """
        if not payload or field not in payload or not payload[field]:
            raise BinderServiceError(f"Payload must include non-empty '{field}'")

    def _wrap_and_log(self, action_name: str, func, *args, **kwargs):
        """
        Execute func and map any exception to BinderServiceError with logging.

        Returns:
            Any: result of func(*args, **kwargs)
        """
        try:
            self._logger.debug("binder_service: performing action %s with args=%s kwargs=%s",
                               action_name, args, {k: "REDACTED" if k.lower().endswith("_token") else v for k, v in kwargs.items()})
            return func(*args, **kwargs)
        except BinderServiceError:
            # let BinderServiceError bubble through unchanged
            raise
        except Exception as exc:  # catch and rewrap all binder-level exceptions
            self._logger.exception("binder_service: error during %s", action_name)
            raise BinderServiceError(f"Error performing '{action_name}': {exc}") from exc

    # ------- Public API: User operations -------

    def create_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a user and set them as the current user in the binder.

        Args:
            user (dict): user payload. MUST include 'id'.

        Returns:
            dict: created user record (as returned by binder.create).

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        self._ensure_id(user, "id")
        created = self._wrap_and_log("create_user", self._binder.create, user)
        # set current user to avoid hidden state surprises in downstream code
        self.set_current_user(user["id"])
        return created

    def set_current_user(self, user_id: str) -> None:
        """
        Set current user context on the binder.

        Args:
            user_id (str): non-empty user identifier.
        """
        
        if not user_id:
            raise BinderServiceError("user_id cannot be empty")

        # Use the binder's property setter correctly
        def _setter(uid):
            self._binder.current_user = uid

        # Keep logging / wrapper behavior intact
        self._wrap_and_log("set_current_user", _setter, user_id)

    # ------- Public API: Client / Patient operations -------

    def create_client(self, client: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a client (or patient) under the current user context.

        Args:
            client (dict): client payload. MUST include 'id'.

        Returns:
            dict: created client record.

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        self._ensure_id(client, "id")
        return self._wrap_and_log("create_client", self._binder.create_client, client)

    def read_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a client by id.

        Args:
            client_id (str): client identifier.

        Returns:
            Optional[dict]: client dict if found, else None.
        """
        if not client_id:
            raise BinderServiceError("client_id cannot be empty")
        return self._wrap_and_log("read_client", self._binder.read_client, client_id)

    def update_client(self, client_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a client's fields and return the updated client.

        Args:
            client_id (str): id of the client to update.
            patch (dict): partial update document (non-empty).

        Returns:
            dict: updated client document.

        Raises:
            BinderServiceError: on validation or binder failure.
        """
        if not client_id:
            raise BinderServiceError("client_id cannot be empty")
        if not patch:
            raise BinderServiceError("patch cannot be empty")
        self._wrap_and_log("update_client", self._binder.update_client, client_id, patch)
        # return the up-to-date record when possible
        updated = self._wrap_and_log("read_client_after_update", self._binder.read_client, client_id)
        if updated is None:
            # binder might choose to not return the item after update; still treat as success
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
        if not client_id:
            raise BinderServiceError("client_id cannot be empty")
        self._wrap_and_log("delete_client", self._binder.delete_client, client_id)

    # ------- Public API: Interactions (visits/transactions) -------

    def create_interaction(self, client_id: str, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an interaction (visit, transaction) for a given client.

        Args:
            client_id (str): target client id.
            interaction (dict): interaction payload; must be non-empty.

        Returns:
            dict: created interaction record.
        """
        if not client_id:
            raise BinderServiceError("client_id cannot be empty")
        if not interaction:
            raise BinderServiceError("interaction payload cannot be empty")
        return self._wrap_and_log("create_interaction", self._binder.create_interaction, client_id, interaction)

    def list_interactions(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List interactions for a client.

        Args:
            client_id (str): client id.

        Returns:
            list[dict]: list of interactions (empty list if none).
        """
        if not client_id:
            raise BinderServiceError("client_id cannot be empty")
        return self._wrap_and_log("list_interactions", self._binder.list_interactions, client_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from binder import BinderBusiness,FirebaseCrudAdapter
    adapter =FirebaseCrudAdapter('test')
    demo_binder = BinderBusiness(adapter)
    service = BinderService(demo_binder)

    # create user
    user = {"id": "u1", "name": "Alice"}
    print("create_user ->", service.create_user(user))

    # create client
    client = {"id": "c1", "name": "Bob"}
    print("create_client ->", service.create_client(client))

    # add interaction
    interaction = {"id": "i1", "type": "visit", "notes": "Initial checkup"}
    print("create_interaction ->", service.create_interaction("c1", interaction))

    # list interactions
    print("list_interactions ->", service.list_interactions("c1"))

    # update client
    print("update_client ->", service.update_client("c1", {"name": "Bobby"}))

    # read client
    print("read_client ->", service.read_client("c1"))

    # delete client
    service.delete_client("c1")
    print("read_client after delete ->", service.read_client("c1"))
