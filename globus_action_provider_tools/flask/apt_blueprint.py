import functools
import json
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Union, overload

from flask import Blueprint, Response, current_app, g, jsonify, request
from jsonschema.validators import Draft7Validator
from werkzeug.exceptions import BadRequest, NotFound, NotImplemented, Unauthorized

from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionProviderJsonEncoder,
    ActionRequest,
    ActionStatus,
    AuthState,
)
from globus_action_provider_tools.flask import (
    blueprint_error_handler,
    flask_validate_request,
)

ActionStatusReturn = Union[ActionStatus, Tuple[ActionStatus, int]]
ActionStatusType = Callable[[Union[str, ActionStatus], AuthState], ActionStatusReturn]

ActionLogReturn = Dict[str, Any]
ActionLogType = Callable[[str, AuthState], ActionLogReturn]

ActionRunType = Callable[[ActionRequest, AuthState], ActionStatusReturn]
ActionCancelType = ActionStatusType
ActionReleaseType = ActionStatusType

ViewReturn = Union[Tuple[Response, int], Tuple[str, int]]

ActionLoaderType = Tuple[Callable[[str, Any], ActionStatus], Any]
ActionSaverType = Tuple[Callable[[ActionStatus, Any], None], Any]


class ActionProviderBlueprint(Blueprint):
    def __init__(
        self,
        provider_description: ActionProviderDescription,
        *args,
        globus_auth_client_name: Optional[str] = None,
        additional_scopes: Iterable[str] = (),
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

        self.action_loader_plugin: Optional[ActionLoaderType] = None
        self.action_saver_plugin: Optional[ActionSaverType] = None

        self.provider_description = provider_description
        self.input_body_validator = self._load_input_body_validator()
        self.globus_auth_client_name = globus_auth_client_name
        self.additional_scopes = additional_scopes

        self.json_encoder = ActionProviderJsonEncoder
        self.before_request(self._check_token)
        self.register_error_handler(Exception, blueprint_error_handler)

        self.add_url_rule(
            "", "action_introspect", self.action_introspect, methods=["GET"]
        )
        self.add_url_rule(
            "/<string:action_id>/status",
            "action_status",
            self._auto_action_status,
            methods=["GET"],
        )
        self.add_url_rule(
            "/<string:action_id>/cancel",
            "action_cancel",
            self._auto_action_cancel,
            methods=["POST"],
        )

    def register(self, app, options, first_registration=False):
        """
        Override the built in Blueprint register function to allow our
        Blueprint to pull configuration data once it is registered with the
        Flask app to create its internal instance of a TokenChecker.

        We first check the environment to see if a blueprint-specific client ID
        and client secret were provided. If we cannot pull those from the
        environment, we backoff and search for generic client id and secret values.
        """
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
        super().register(app, options, first_registration)

    def action_introspect(self):
        """
        Runs as an Action Provider's introspection endpoint.
        """
        if not g.auth_state.check_authorization(
            self.provider_description.visible_to,
            allow_public=True,
            allow_all_authenticated_users=True,
        ):
            current_app.logger.info(
                f'User "{g.auth_state.effective_identity}" is unauthorized to introspect Action Provider'
            )
            raise NotFound

        return jsonify(self.provider_description), 200

    def action_run(self, func: ActionRunType) -> Callable[[], ViewReturn]:
        """
        Decorates a function to be run as an Action Provider's run endpoint.
        """

        @functools.wraps(func)
        def wrapper() -> ViewReturn:
            if not g.auth_state.check_authorization(
                self.provider_description.runnable_by,
                allow_all_authenticated_users=True,
            ):
                current_app.logger.info(
                    f'User "{g.auth_state.effective_identity}" is unauthorized to run Action'
                )
                raise Unauthorized()

            # Ensure incoming request conforms to ActionRequest schema
            result = flask_validate_request(request)
            if result.error_msg:
                raise BadRequest(result.error_msg)

            request_json = request.get_json(force=True)
            action_request = ActionRequest(**request_json)

            # Ensure incoming Action body conforms to Action Provider schema
            self._validate_input(action_request.body)
            status = func(action_request, g.auth_state)
            self._save_action(status)
            return self._action_status_return_to_view_return(status, 202)

        self.add_url_rule("/run", func.__name__, wrapper, methods=["POST"])
        print(f'Registered action run plugin "{func.__name__}"')
        return wrapper

    @overload
    def action_status(self, func: Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_status can accept a str or ActionStatus as the first arg type
        NOTE: typing_extensions.Protocol would be better if not for it's poor
        error messages
        """
        ...

    @overload
    def action_status(
        self, func: Callable[[ActionStatus, AuthState], ActionStatusReturn]
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
        print(f'Registered action status plugin "{func.__name__}"')

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
            try:
                result = self._action_status(action_id, g.auth_state)
            except AttributeError:
                raise NotImplemented("No status endpoint is available")
        return self._action_status_return_to_view_return(result, 200)

    @overload
    def action_cancel(self, func: Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_cancel can accept a str or ActionStatus as the first arg type
        """
        ...

    @overload
    def action_cancel(
        self, func: Callable[[ActionStatus, AuthState], ActionStatusReturn]
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
        print(f'Registered action cancel plugin "{func.__name__}"')

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
            try:
                result = self._action_cancel(action_id, g.auth_state)
            except AttributeError:
                raise NotImplemented("No cancel endpoint is available")
        return self._action_status_return_to_view_return(result, 200)

    @overload
    def action_release(self, func: Callable[[str, AuthState], ActionStatusReturn]):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_release can accept a str or ActionStatus as the first arg type
        """
        ...

    @overload
    def action_release(
        self, func: Callable[[ActionStatus, AuthState], ActionStatusReturn]
    ):
        """
        Using these stubs w/ @overload tells mypy that the actual implementation
        for action_release can accept a str or ActionStatus as the first arg type
        """
        ...

    def action_release(self, func) -> Callable[[str], ViewReturn]:
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

            status = func(action_id, g.auth_state)  # type: ignore
            return self._action_status_return_to_view_return(status, 200)

        self.add_url_rule(
            "/<string:action_id>/release",
            func.__name__,
            wrapper,
            methods=["POST"],
        )
        print(f'Registered action release plugin "{func.__name__}"')
        return wrapper

    def action_log(self, func: ActionLogType) -> Callable[[str], ViewReturn]:
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

        self.add_url_rule(
            "/<string:action_id>/log", func.__name__, wrapper, methods=["GET"]
        )
        print(f'Registered action log plugin "{func.__name__}"')
        return wrapper

    def register_action_loader(self, storage_backend: Any):
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
            print(f"Registered action loader '{func.__name__}'")

        return wrapper

    def _load_action_by_id(self, action_id: str) -> ActionStatus:
        """
        If the actiond_id is not found in the registered action_loader, we
        assume the ActionStatus is non-recoverable.
        """
        if self.action_loader_plugin is None:
            raise NotFound

        func, backend = self.action_loader_plugin
        action = func(action_id, backend)
        if action:
            print(f"Found action via plugin: {func.__name__}")
            return action
        raise NotFound

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
            print(f"Registered action saver '{func.__name__}'")

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
        print(f"Saved action via plugin {func.__name__}")

    def _check_token(self) -> None:
        """
        Parses a token from a request to generate an auth_state object which is
        then made available as the second argument to decorated functions.
        """
        access_token = (
            request.headers.get("Authorization", "").strip().lstrip("Bearer ")
        )
        auth_state = self.checker.check_token(access_token)
        g.auth_state = auth_state

    def _load_input_body_validator(self) -> Union[Draft7Validator, None]:
        """
        Creates a JSON Validator object to be used to verify that the body of a
        RUN request conforms to the Action Provider's defined schema. In the
        event that no schema was provided when defining the Blueprint, no
        validator is created and no validation occurs.
        """
        if isinstance(self.provider_description.input_schema, str):
            input_schema = json.loads(self.provider_description.input_schema)
        else:
            input_schema = self.provider_description.input_schema

        if input_schema is not None:
            input_body_validator = Draft7Validator(input_schema)
        else:
            input_body_validator = None

        return input_body_validator

    def _validate_input(self, input: Dict[str, Any]) -> None:
        """
        Use a created JSON Validator to verify the input body of an incoming
        request conforms to the defined JSON schema. In the event that the
        validation reports any errors, a BadRequest exception gets raised.
        """
        if self.input_body_validator is None:
            return

        errors = self.input_body_validator.iter_errors(input)
        error_messages = []
        for error in errors:
            if error.path:
                # Elements of the error path may be integers or other non-string types,
                # but we need strings for use with join()
                error_path_for_message = ".".join([str(x) for x in error.path])
                error_message = (
                    f"'{error_path_for_message}' invalid due to {error.message}"
                )
            else:
                error_message = error.message
            error_messages.append(error_message)

        if error_messages:
            message = "; ".join(error_messages)
            raise BadRequest(message)

    def _action_status_return_to_view_return(
        self, status: ActionStatusReturn, default_status_code: int
    ) -> ViewReturn:
        """
        Helper function to return a ActionStatusReturn object as a valid Flask
        response.
        """
        if isinstance(status, ActionStatus):
            status_code = default_status_code
        elif isinstance(status, tuple):
            status, status_code = status
        return jsonify(status), status_code
