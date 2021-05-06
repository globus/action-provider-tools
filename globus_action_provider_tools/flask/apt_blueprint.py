import functools
import typing as t

from flask import Blueprint, blueprints, current_app, g, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest as WerkzeugBadRequest

from globus_action_provider_tools.authentication import AuthState, TokenChecker
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
    ActionCancelType,
    ActionEnumerationType,
    ActionLoaderType,
    ActionLogType,
    ActionRunType,
    ActionSaverType,
    ActionStatusReturn,
    ActionStatusType,
    ViewReturn,
)


class ActionProviderBlueprint(Blueprint):
    def __init__(
        self,
        provider_description: ActionProviderDescription,
        *args,
        globus_auth_client_name: t.Optional[str] = None,
        additional_scopes: t.Iterable[str] = (),
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

        self.action_loader_plugin: t.Optional[ActionLoaderType] = None
        self.action_saver_plugin: t.Optional[ActionSaverType] = None

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

        # If using an action-loader, it's possible that the status and cancel
        # endpoints do not need to be implemented. Therefore, we initialize the
        # API route for those operations with "auto" functions that
        # Old-style AP API endpoints
        self.add_url_rule(
            "/<string:action_id>/status",
            None,
            self._auto_action_status,
            methods=["GET"],
        )
        self.add_url_rule(
            "/<string:action_id>/cancel",
            None,
            self._auto_action_cancel,
            methods=["POST"],
        )
        # Add new-style AP API endpoints
        self.add_url_rule(
            "/actions/<string:action_id>",
            "action_status",
            self._auto_action_status,
            methods=["GET"],
        )
        self.add_url_rule(
            "/actions/<string:action_id>/cancel",
            "action_cancel",
            self._auto_action_cancel,
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
            current_app.logger.info(g.auth_state.errors)
            current_app.logger.info(
                f"{g.auth_state.effective_identity} is unauthorized to introspect Action Provider"
            )
            raise UnauthorizedRequest

        return jsonify(self.provider_description), 200

    def action_enumerate(self, func: ActionEnumerationType):
        """
        Decorates a function to be run as an Action Provider's enumeration
        endpoint.
        """

        @functools.wraps(func)
        def wrapper():
            if not g.auth_state.check_authorization(
                self.provider_description.runnable_by,
                allow_public=True,
                allow_all_authenticated_users=True,
            ):
                current_app.logger.info(g.auth_state.errors)
                current_app.logger.info(
                    f"{g.auth_state.effective_identity} is unauthorized to enumerate "
                    "Actions"
                )
                raise UnauthorizedRequest

            valid_statuses = set(e.name.casefold() for e in ActionStatusValue)
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
            enumeration = func(g.auth_state, query_params)
            return jsonify(enumeration), 200

        self.add_url_rule(
            "/actions",
            "action_enumerate",
            wrapper,
            methods=["GET"],
        )
        return wrapper

    def action_run(self, func: ActionRunType) -> t.Callable[[], ViewReturn]:
        """
        Decorates a function to be run as an Action Provider's run endpoint.
        """

        @functools.wraps(func)
        def wrapper() -> ViewReturn:
            if not g.auth_state.check_authorization(
                self.provider_description.runnable_by,
                allow_all_authenticated_users=True,
            ):
                current_app.logger.info(g.auth_state.errors)
                current_app.logger.info(
                    f"{g.auth_state.effective_identity} is unauthorized to run Action"
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
                status = func(action_request, g.auth_state)
            except ValidationError as ve:
                current_app.logger.error(
                    f"ActionProvider attempted to create a non-conformant ActionStatus "
                    f"in {func.__name__}: {ve.errors()}"
                )
                raise ActionProviderError

            self._save_action(status)
            return action_status_return_to_view_return(status, 202)

        # Add new and old-style AP API endpoints
        self.add_url_rule("/run", None, wrapper, methods=["POST"])
        self.add_url_rule("/actions", func.__name__, wrapper, methods=["POST"])
        return wrapper

    @t.overload
    def action_resume(self, func: t.Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_resume can accept a str or ActionStatus as the first arg type
        NOTE: typing_extensions.Protocol would be better if not for it's poor
        error messages
        """
        ...

    @t.overload
    def action_resume(
        self, func: t.Callable[[ActionStatus, AuthState], ActionStatusReturn]
    ):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_resume can accept a str or ActionStatus as the first arg type
        """
        ...

    def action_resume(self, func) -> t.Callable[[str], ViewReturn]:
        """
        Decorates a function to be run as an Action Provider's resume endpoint.
        """

        @functools.wraps(func)
        def wrapper(action_id: str) -> ViewReturn:
            # Attempt to use a user-defined function to lookup the Action based
            # on its action_id. If an action is found, authorize access to it
            if self.action_loader_plugin:
                action = self._load_action_by_id(action_id)
                authorize_action_access_or_404(action, g.auth_state)

            status = func(action_id, g.auth_state)
            return action_status_return_to_view_return(status, 200)

        # Add new and old-style AP API endpoints
        self.add_url_rule("/<string:action_id>/resume", None, wrapper, methods=["POST"])
        self.add_url_rule(
            "/actions/<string:action_id>/resume",
            "action_resume",
            wrapper,
            methods=["POST"],
        )
        return wrapper

    @t.overload
    def action_status(self, func: t.Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_status can accept a str or ActionStatus as the first arg type
        NOTE: typing_extensions.Protocol would be better if not for it's poor
        error messages
        """
        ...

    @t.overload
    def action_status(
        self, func: t.Callable[[ActionStatus, AuthState], ActionStatusReturn]
    ):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_status can accept a str or ActionStatus as the first arg type
        """
        ...

    def action_status(self, func) -> None:
        """
        Decorates a function to be run as an Action Provider's status endpoint.
        """
        self._action_status: ActionStatusType = func

    def _auto_action_status(self, action_id: str) -> ViewReturn:
        """
        Attempts to load an action_status via its action_id using an
        action_loader. If an action is successfully loaded, view access by the
        requesting user is verified before returning it to the caller.
        """
        # Attempt to use a user-defined function to lookup the Action based
        # on its action_id. If an action is found, verify access to it
        if self.action_loader_plugin:
            action = self._load_action_by_id(action_id)
            authorize_action_access_or_404(action, g.auth_state)
            try:
                result = self._action_status(action, g.auth_state)
            except AttributeError:
                # Once an action_loader is registered, there is no reason to
                # register an action_status. Therefore, an exception here is ok,
                # in which case just return the bare action as the result
                result = action
        else:
            if not hasattr(self, "_action_status"):
                current_app.logger.error("ActionProvider has no action status endpoint")
                raise ActionProviderError
            try:
                # It's possible the user will attempt to make a malformed ActionStatus -
                # pydantic won't like that. So handle the error with a 500
                result = self._action_status(action_id, g.auth_state)
            except ValidationError as ve:
                current_app.logger.error(
                    f"ActionProvider attempted to create a non-conformant ActionStatus "
                    f"in {self._action_status.__name__}: {ve.errors()}"
                )
                raise ActionProviderError
        return action_status_return_to_view_return(result, 200)

    @t.overload
    def action_cancel(self, func: t.Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_cancel can accept a str or ActionStatus as the first arg type
        """
        ...

    @t.overload
    def action_cancel(
        self, func: t.Callable[[ActionStatus, AuthState], ActionStatusReturn]
    ):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_cancel can accept a str or ActionStatus as the first arg type
        """
        ...

    def action_cancel(self, func) -> None:
        """
        Decorates a function to be run as an Action Provider's cancel endpoint.
        """
        self._action_cancel: ActionCancelType = func

    def _auto_action_cancel(self, action_id: str) -> ViewReturn:
        """
        Executes a user-defined function for cancelling an Action.
        """
        # Attempt to use a user-defined function to lookup the Action based
        # on its action_id. If an action is found, verify access to it
        if self.action_loader_plugin:
            action = self._load_action_by_id(action_id)
            authorize_action_management_or_404(action, g.auth_state)
            try:
                result = self._action_cancel(action, g.auth_state)
            except AttributeError:
                # Once an action_loader is registered, if the ActionProvider is
                # synchronous, there is no reason to register an action_cancel.
                # Therefore, an exception here might be ok, in which case just
                # return the bare action as the result
                result = action
            finally:
                self._save_action(action)
        else:
            if not hasattr(self, "_action_cancel"):
                current_app.logger.error("ActionProvider has no action cancel endpoint")
                raise ActionProviderError

            try:
                result = self._action_cancel(action_id, g.auth_state)
            except ValidationError as ve:
                current_app.logger.error(
                    f"ActionProvider attempted to create a non-conformant ActionStatus "
                    f"in {self._action_cancel.__name__}: {ve.errors()}"
                )
                raise ActionProviderError
        return action_status_return_to_view_return(result, 200)

    @t.overload
    def action_release(self, func: t.Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_release can accept a str or ActionStatus as the first arg type
        """
        ...

    @t.overload
    def action_release(
        self, func: t.Callable[[ActionStatus, AuthState], ActionStatusReturn]
    ):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_release can accept a str or ActionStatus as the first arg type
        """
        ...

    def action_release(self, func) -> t.Callable[[str], ViewReturn]:
        """
        Decorates a function to be run as an Action Provider's release endpoint.
        """

        @functools.wraps(func)
        def wrapper(action_id: str) -> ViewReturn:
            # Attempt to use a user-defined function to lookup the Action based
            # on its action_id. If an action is found, authorize access to it
            if self.action_loader_plugin:
                action = self._load_action_by_id(action_id)
                authorize_action_management_or_404(action, g.auth_state)

            try:
                status = func(action_id, g.auth_state)
            except ValidationError as ve:
                current_app.logger.error(
                    f"ActionProvider attempted to create a non-conformant ActionStatus "
                    f"in {func.__name__}: {ve.errors()}"
                )
                raise ActionProviderError

            return action_status_return_to_view_return(status, 200)

        # Add new and old-style AP API endpoints
        self.add_url_rule(
            "/<string:action_id>/release",
            None,
            wrapper,
            methods=["POST"],
        )
        self.add_url_rule(
            "/actions/<string:action_id>",
            "action_release",
            wrapper,
            methods=["DELETE"],
        )
        return wrapper

    def action_log(self, func: ActionLogType) -> t.Callable[[str], ViewReturn]:
        """
        Decorates a function to be run an an Action Provider's logging endpoint.
        """

        @functools.wraps(func)
        def wrapper(action_id: str) -> ViewReturn:
            # Attempt to use a user-defined function to lookup the Action based
            # on its action_id. If an action is found, authorize access to it
            if self.action_loader_plugin:
                action = self._load_action_by_id(action_id)
                authorize_action_access_or_404(action, g.auth_state)

            status = func(action_id, g.auth_state)
            return jsonify(status), 200

        # Add new and old-style AP API endpoints
        self.add_url_rule("/<string:action_id>/log", None, wrapper, methods=["GET"])
        self.add_url_rule(
            "/actions/<string:action_id>/log", "action_log", wrapper, methods=["GET"]
        )
        return wrapper

    def register_action_loader(self, storage_backend: t.Any):
        """
        Decorates a function that will be used to lookup an ActionStatus by its
        action_id. Multiple action_loaders with different backends can be
        registered and each will be used sequentially when attempting to lookup
        an ActionStatus. If any action_loaders are registered and they fail to
        lookup an ActionStatus, a 404 error will be thrown.

        If an action_loader is registered, it will be used by the status,
        cancel, release, and log endpoints. Those endpoints will then provide
        the ActionStatus to the user-defined route functions.
        """

        # TODO figure out how to get a type annotation working on this inner func
        def wrapper(func):
            self.action_loader_plugin = (func, storage_backend)

        return wrapper

    def _load_action_by_id(self, action_id: str) -> ActionStatus:
        """
        If the actiond_id is not found in the registered action_loader, we
        assume the ActionStatus is non-recoverable.
        """
        if self.action_loader_plugin is None:
            raise ActionNotFound

        func, backend = self.action_loader_plugin
        action = func(action_id, backend)
        if action:
            return action
        raise ActionNotFound

    def register_action_saver(self, storage_backend):
        """
        Decorates a function that will be used to save an ActionStatus. Multiple
        action_savers with different backends can be registered and each backend
        will save a copy of the ActionStatus. If any action_savers are
        registered and they fail to save an ActionStatus, an error will be
        thrown.

        #TODO pickup here, what should the behavior for an action_saver be? When
        should it be called?
        # TODO the return of the action_loader is an action, the return for the plugins
        # are actionStatusReturns, which are DIFFERENT [THANKS MYPY]
        """

        def wrapper(func):
            self.action_saver_plugin: ActionSaverType = (func, storage_backend)

        return wrapper

    def _save_action(self, action: ActionStatusReturn) -> None:
        """
        Executes an action_saver to store the ActionStatus in the specified
        backend.
        """
        if self.action_saver_plugin is None:
            return
        if not isinstance(action, ActionStatus):
            action, _ = action

        func, backend = self.action_saver_plugin
        func(action, backend)

    def _check_token(self) -> None:
        """
        Parses a token from a request to generate an auth_state object which is
        then made available as the second argument to decorated functions.
        """
        g.auth_state = check_token(request, self.checker)
