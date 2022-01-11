import typing as t

from flask import Blueprint, blueprints, current_app, g, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest as WerkzeugBadRequest

from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionProviderJsonEncoder,
    ActionStatus,
    ActionStatusValue,
)
from globus_action_provider_tools.flask.exceptions import (
    ActionNotFound,
    ActionProviderError,
    BadActionRequest,
    UnauthorizedRequest,
)
from globus_action_provider_tools.flask.helpers import (
    action_status_return_to_view_return,
    blueprint_error_handler,
    check_token,
    get_input_body_validator,
    parse_query_args,
    query_args_to_enum,
    validate_input,
)
from globus_action_provider_tools.flask.types import (
    ActionCallbackReturn,
    ActionCancelCallback,
    ActionEnumerationCallback,
    ActionLogCallback,
    ActionReleaseCallback,
    ActionResumeCallback,
    ActionRunCallback,
    ActionStatusCallback,
)
from globus_action_provider_tools.storage import AbstractActionRepository


class ActionProviderBlueprint(Blueprint):
    def __init__(
        self,
        provider_description: ActionProviderDescription,
        *args,
        globus_auth_client_name: t.Optional[str] = None,
        additional_scopes: t.Iterable[str] = (),
        action_repository: t.Optional[AbstractActionRepository] = None,
        **kwarg,
    ):
        """Create a new ActionProviderBlueprint. All arguments not listed here are the
        same as a Flask Blueprint.

        :param provider_description: A Provider Description which will be
        returned from introspection calls to this Blueprint.

        :param globus_auth_client_name: The name of the Globus Auth Client (also
        known as the resource server name). This will be used to validate the
        intended audience for tokens passed to the operations on this
        Blueprint. By default, the client id will be used for checkign audience,
        and unless the client has explicitly been given a resource server name
        in Globus Auth, this will be proper behavior.

        :param additional_scopes: Additional scope strings the Action Provider
        should allow scopes in addition to the one specified by the
        ``globus_auth_scope`` value of the input provider description. Only
        needed if more than one scope has been allocated for the Action
        Provider's Globus Auth client_id.
        """

        super().__init__(*args, **kwarg)

        self.action_repo = action_repository
        self.provider_description = provider_description
        self.input_body_validator = get_input_body_validator(provider_description)
        self.globus_auth_client_name = globus_auth_client_name
        self.additional_scopes = additional_scopes

        self.json_encoder = ActionProviderJsonEncoder
        self.before_request(self._check_token)
        self.register_error_handler(Exception, blueprint_error_handler)
        self.record_once(self._create_token_checker)

        self.add_url_rule(
            "/",
            "action_introspect",
            self._action_introspect,
            methods=["GET"],
            strict_slashes=False,
        )

        # If using an action-repository, the status and cancel endpoints do not
        # need to be implemented. Therefore, we initialize the API route for
        # those operations with "auto" functions
        # Old style API endpoints
        self.add_url_rule(
            "/<string:action_id>/status",
            None,
            self._action_status,
            methods=["GET"],
        )
        self.add_url_rule(
            "/<string:action_id>/cancel",
            None,
            self._action_cancel,
            methods=["POST"],
        )
        # Add new-style AP API endpoints
        self.add_url_rule(
            "/actions/<string:action_id>",
            "action_status",
            self._action_status,
            methods=["GET"],
        )
        self.add_url_rule(
            "/actions/<string:action_id>/cancel",
            "action_cancel",
            self._action_cancel,
            methods=["POST"],
        )

    def _create_token_checker(self, setup_state: blueprints.BlueprintSetupState):
        app = setup_state.app
        provider_prefix = self.name.upper() + "_"
        client_id = app.config.get(provider_prefix + "CLIENT_ID")
        client_secret = app.config.get(provider_prefix + "CLIENT_SECRET")

        if not client_id or not client_secret:
            client_id = app.config.get("CLIENT_ID")
            client_secret = app.config.get("CLIENT_SECRET")

        scopes = [self.provider_description.globus_auth_scope]
        scopes.extend(self.additional_scopes)

        app.logger.info(
            f"Initializing TokenChecker for client {client_id} and secret "
            f"***{client_secret[-5:]}"
        )
        self.checker = TokenChecker(
            client_id=client_id,
            client_secret=client_secret,
            expected_scopes=scopes,
            expected_audience=self.globus_auth_client_name,
        )

    def _action_introspect(self):
        """
        Runs as an Action Provider's introspection endpoint.
        """
        if not g.auth_state.check_authorization(
            self.provider_description.visible_to,
            allow_public=True,
            allow_all_authenticated_users=True,
        ):
            current_app.logger.info(
                f"{g.auth_state.effective_identity} is unauthorized to introspect Action "
                f"Provider due {g.auth_state.errors}"
            )
            raise UnauthorizedRequest

        return jsonify(self.provider_description), 200

    def _action_enumerate(self):
        if not g.auth_state.check_authorization(
            self.provider_description.runnable_by,
            allow_public=True,
            allow_all_authenticated_users=True,
        ):
            current_app.logger.info(
                f"{g.auth_state.effective_identity} is unauthorized to enumerate "
                f"Actions due to {g.auth_state.error}"
            )
            raise UnauthorizedRequest

        valid_statuses = {e.name.casefold() for e in ActionStatusValue}
        statuses = parse_query_args(
            request,
            arg_name="status",
            default_value="active",
            valid_vals=valid_statuses,
        )
        statuses = query_args_to_enum(statuses, ActionStatusValue)
        roles = parse_query_args(
            request,
            arg_name="roles",
            default_value="creator_id",
            valid_vals={"creator_id", "monitor_by", "manage_by"},
        )
        query_params = {"statuses": statuses, "roles": roles}
        enumeration = self.action_enumerate_callback(g.auth_state, query_params)
        return jsonify(enumeration), 200

    def action_enumerate(self, func: ActionEnumerationCallback):
        """
        Registers a function to run as the Action Provider's enumeration endpoint.
        """
        self.action_enumerate_callback = func
        self.add_url_rule(
            "/actions", "action_enumerate", self._action_enumerate, methods=["GET"]
        )
        return func

    def _action_run(self):
        if not g.auth_state.check_authorization(
            self.provider_description.runnable_by,
            allow_all_authenticated_users=True,
        ):
            current_app.logger.info(
                f"{g.auth_state.effective_identity} is unauthorized to run Action due to {g.auth_state.errors}"
            )
            raise UnauthorizedRequest

        try:
            json_input = request.get_json(force=True)
        except WerkzeugBadRequest:
            current_app.logger.info(
                f"{g.auth_state.effective_identity} submitted input that could not "
                f"be parsed as JSON: {str(request.data)}"
            )
            raise BadActionRequest("Invalid JSON")
        try:
            action_request = validate_input(json_input, self.input_body_validator)
        except BadActionRequest as err:
            current_app.logger.info(
                f"{g.auth_state.effective_identity} submitted invalid input: "
                f"{err.get_body()}"
            )
            raise

        # It's possible the user will attempt to make a malformed ActionStatus -
        # pydantic won't like that. So log and handle the error with a 500
        try:
            status = self.action_run_callback(action_request, g.auth_state)
        except ValidationError as ve:
            current_app.logger.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus "
                f"in {self.action_run_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError

        if self.action_repo:
            self._save_action(self.action_repo, status)
        return action_status_return_to_view_return(status, 202)

    def action_run(self, func: ActionRunCallback):
        """
        Registers a function to run as the Action Provider's run endpoint.
        """
        self.action_run_callback: ActionRunCallback = func
        self.add_url_rule("/run", None, self._action_run, methods=["POST"])
        self.add_url_rule("/actions", func.__name__, self._action_run, methods=["POST"])
        return func

    def _action_resume(self, action_id: str):
        # Attempt to lookup the Action based on its action_id if there was an
        # Action Repo defined. If an action is found, verify access to it.
        action = None
        if self.action_repo is not None:
            action = self._load_action_by_id(self.action_repo, action_id)
            authorize_action_management_or_404(action, g.auth_state)

        try:
            if action:
                result = self.action_resume_callback(action, g.auth_state)  # type: ignore
            else:
                result = self.action_resume_callback(action_id, g.auth_state)  # type: ignore
        except AttributeError:
            current_app.logger.error("ActionProvider has no action resume endpoint")
            raise ActionProviderError
        except ValidationError as ve:
            current_app.logger.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus "
                f"in {self.action_resume_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError

        if self.action_repo:
            self._save_action(self.action_repo, result)
        return action_status_return_to_view_return(result, 200)

    def action_resume(self, func: ActionResumeCallback):
        """
        Decorates a function to be run as an Action Provider's resume endpoint.
        """
        self.action_resume_callback: ActionResumeCallback = func
        self.add_url_rule(
            "/<string:action_id>/resume", None, self._action_resume, methods=["POST"]
        )
        self.add_url_rule(
            "/actions/<string:action_id>/resume",
            func.__name__,
            self._action_resume,
            methods=["POST"],
        )
        return func

    def action_status(self, func: ActionStatusCallback):
        """
        Registers a function to run as the Action Provider's status endpoint.
        """
        self.action_status_callback: ActionStatusCallback = func
        return func

    def _action_status(self, action_id: str):
        """
        Attempts to load an action_status via its action_id using an
        action_loader. If an action is successfully loaded, view access by the
        requesting user is verified before returning it to the caller.
        """
        # Attempt to lookup the Action based on its action_id if there was an
        # Action Repo defined. If an action is found, verify access to it.
        action = None
        if self.action_repo is not None:
            action = self._load_action_by_id(self.action_repo, action_id)
            authorize_action_access_or_404(action, g.auth_state)

        try:
            if action:
                result = self.action_status_callback(action, g.auth_state)  # type: ignore
            else:
                result = self.action_status_callback(action_id, g.auth_state)  # type: ignore
        except AttributeError:
            # If an ActionRepo is registered, there is no need to register an
            # action_cancel callback. Therefore, an exception here might be ok
            if action is None:
                current_app.logger.error("ActionProvider has no action status endpoint")
                raise ActionProviderError
            else:
                result = action
        except ValidationError as ve:
            current_app.logger.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus "
                f"in {self.action_status_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError

        if self.action_repo:
            self._save_action(self.action_repo, result)
        return action_status_return_to_view_return(result, 200)

    def action_cancel(self, func: ActionCancelCallback):
        """
        Decorates a function to be run as an Action Provider's cancel endpoint.
        """
        self.action_cancel_callback: ActionCancelCallback = func
        return func

    def _action_cancel(self, action_id: str):
        """
        Executes a user-defined function for cancelling an Action.
        """
        # Attempt to lookup the Action based on its action_id if there was an
        # Action Repo defined. If an action is found, verify access to it.
        action = None
        if self.action_repo is not None:
            action = self._load_action_by_id(self.action_repo, action_id)
            authorize_action_management_or_404(action, g.auth_state)

        try:
            if action:
                result = self.action_cancel_callback(action, g.auth_state)  # type: ignore
            else:
                result = self.action_cancel_callback(action_id, g.auth_state)  # type: ignore
        except AttributeError:
            # If an ActionRepo is registered, there is no need to register an
            # action_cancel callback. Therefore, an exception here might be ok
            if action is None:
                current_app.logger.error("ActionProvider has no action cancel endpoint")
                raise ActionProviderError
            else:
                result = action
        except ValidationError as ve:
            current_app.logger.error(
                f"Action Provider attempted to create a non-conformant ActionStatus "
                f"in {self.action_cancel_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError

        if self.action_repo:
            self._save_action(self.action_repo, result)
        return action_status_return_to_view_return(result, 200)

    def action_release(self, func: ActionReleaseCallback):
        """
        Decorates an Action Provider's release endpoint
        """
        self.action_release_callback: ActionReleaseCallback = func
        self.add_url_rule(
            "/<string:action_id>/release",
            func.__name__,
            self._action_release,
            methods=["POST"],
        )
        self.add_url_rule(
            "/actions/<string:action_id>",
            func.__name__,
            self._action_release,
            methods=["DELETE"],
        )
        return func

    def _action_release(self, action_id: str):
        """
        Decorates a function to be run as an Action Provider's release endpoint.
        """
        # Attempt to lookup the Action based on its action_id if there was an
        # Action Repo defined. If an action is found, verify access to it.
        action = None
        if self.action_repo is not None:
            action = self._load_action_by_id(self.action_repo, action_id)
            authorize_action_management_or_404(action, g.auth_state)

        try:
            if action:
                result = self.action_release_callback(action, g.auth_state)  # type: ignore
            else:
                result = self.action_release_callback(action_id, g.auth_state)  # type: ignore
        except ValidationError as ve:
            current_app.logger.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus "
                f"in {self.action_release_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError

        return action_status_return_to_view_return(result, 200)

    def action_log(self, func: ActionLogCallback):
        """
        Decorates a function to be run an an Action Provider's logging endpoint.
        """
        self.action_log_callback: ActionLogCallback = func
        self.add_url_rule(
            "/<string:action_id>/log", func.__name__, self._action_log, methods=["GET"]
        )
        self.add_url_rule(
            "/actions/<string:action_id>/log",
            func.__name__,
            self._action_log,
            methods=["GET"],
        )
        return func

    def _action_log(self, action_id: str):
        # Attempt to use a user-defined function to lookup the Action based
        # on its action_id. If an action is found, authorize access to it
        action = None
        if self.action_repo is not None:
            action = self._load_action_by_id(self.action_repo, action_id)
            authorize_action_access_or_404(action, g.auth_state)

        status = self.action_log_callback(action_id, g.auth_state)
        return jsonify(status), 200

    def _load_action_by_id(
        self, repo: AbstractActionRepository, action_id: str
    ) -> ActionStatus:
        """
        If the actiond_id is not found in the registered action_loader, we
        assume the ActionStatus is non-recoverable and return a helpful 404.
        """
        action = repo.get(action_id)
        if action:
            return action
        current_app.logger.warning(f"No Action with ID {action_id} found in repo")
        raise ActionNotFound

    def _save_action(
        self, repo: AbstractActionRepository, result: ActionCallbackReturn
    ) -> None:
        """
        Executes an action_saver to store the ActionStatus in the specified
        backend.
        """
        if isinstance(result, ActionStatus):
            action = result
        elif isinstance(result, tuple):
            action = result[0]
        if not isinstance(action, ActionStatus):
            current_app.logger.warning(
                f"Attempted to save a non ActionStatus: {action}"
            )
            raise ActionProviderError
        repo.store(action)

    def _check_token(self) -> None:
        """
        Parses a token from a request to generate an auth_state object which is
        then made available as the second argument to decorated functions.
        """
        g.auth_state = check_token(request, self.checker)
        if g.auth_state.effective_identity is None:
            current_app.logger.info(
                f"Request failed authentication due to: {g.auth_state.errors}"
            )
