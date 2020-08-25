import functools
import inspect
import json
import logging
import time
from functools import singledispatch, update_wrapper
from typing import Any, Callable, Dict, Optional, Tuple, Union

from flask import Blueprint, Request, Response, current_app, g, jsonify, request
from jsonschema.validators import Draft7Validator
from werkzeug.exceptions import BadRequest, NotFound, NotImplemented, Unauthorized

from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
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
ActionLogReturn = Dict[str, Any]
ViewReturn = Union[Tuple[Response, int], Tuple[str, int]]

ActionRunType = Callable[[ActionRequest, AuthState], ActionStatusReturn]
ActionStatusType = Union[
    Callable[[str, AuthState], ActionStatusReturn],
    Callable[[ActionStatus, AuthState], ActionStatusReturn],
]
ActionCancelType = ActionStatusType
ActionReleaseType = ActionStatusType
ActionLogType = Callable[[str, AuthState], ActionLogReturn]


def methdispatch(func):
    """
    Allows singledispatch to work on a mix of Class methods and regular functions.
    Huge shoutout to https://stackoverflow.com/a/24602374.

    This decorator decorates a base function which we want to call in a
    "generic" way where generic means that the first argument to the function
    call can have multiple types, and the function called differs
    according to the arg type supplied. The dispatch is essentially a lookup
    based on type:

    {
        class:Object: my_func,
        class:Str: my_func_for_strs,
        class:Int: my_func_for_ints,
        class:ActionStatus: my_func_for_ActionStatus
    }
    """
    dispatcher = singledispatch(func)

    def wrapper(*args, **kw):
        matching_func = dispatcher.dispatch(args[1].__class__)

        # If the dispatched function is user-supplied, it isn't an instance
        # method so we remove the first arg which is the "self" reference
        if matching_func is not dispatcher.dispatch(object):
            args = args[1:]

        return matching_func(*args, **kw)

    wrapper.register = dispatcher.register
    update_wrapper(wrapper, func)
    return wrapper


class ActionProviderBlueprint(Blueprint):
    def __init__(
        self, provider_description, *args, **kwarg,
    ):
        super().__init__(*args, **kwarg)

        self.action_status_plugin: ActionStatusType = None
        self.action_cancel_plugin: ActionCancelType = None
        self.action_loader_plugin = None
        self.action_saver_plugin = None

        self.provider_description = provider_description
        self.input_body_validator = self._load_input_body_validator()

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

        self.checker = TokenChecker(
            client_id=client_id,
            client_secret=client_secret,
            expected_scopes=[self.provider_description.globus_auth_scope],
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
            return self._action_status_return_to_view_return(status, 201)

        self.add_url_rule("/run", func.__name__, wrapper, methods=["POST"])
        print(f'Registered action run plugin "{func.__name__}"')
        return wrapper

    @methdispatch
    def _generic_action_status(self, *args, **kwargs):
        raise NotImplemented(
            f"No action_status function registered to handle type {type(args[0])}"
        )

    def action_status(self, func: ActionStatusType):
        """
        Decorates a function to be run as an Action Provider's status endpoint.
        """
        _, first_param = list(inspect.signature(func).parameters.items())[0]
        if first_param.annotation == first_param.empty:
            # There's no annotation available, assume the function handles str
            self._generic_action_status.register(str, func)
        else:
            self._generic_action_status.register(first_param.annotation, func)
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
                action = self._generic_action_status(action, g.auth_state)
            except NotImplemented:
                # Once an action_loader is registered, there is no reason to
                # register an action_status. Therefore, an exception here is ok
                pass
        else:
            action = self._generic_action_status(action_id, g.auth_state)
        return self._action_status_return_to_view_return(action, 200)

    @methdispatch
    def _generic_action_cancel(self, *args, **kwargs):
        raise NotImplemented(
            f"No action_cancel function registered to handle type {type(args[0])}"
        )

    def action_cancel(self, func: ActionCancelType) -> None:
        """
        Decorates a function to be run as an Action Provider's cancel endpoint.
        """
        _, first_param = list(inspect.signature(func).parameters.items())[0]
        if first_param.annotation == first_param.empty:
            # There's no annotation available, assume the function handles str
            self._generic_action_cancel.register(str, func)
        else:
            self._generic_action_cancel.register(first_param.annotation, func)
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
                action = self._generic_action_cancel(action, g.auth_state)
            except NotImplemented as e:
                # Once an action_loader is registered, if the ActionProvider is
                # synchronous, there is no reason to register an action_cancel.
                # Therefore, an exception here might be ok
                pass
            finally:
                self._save_action(action)
        else:
            action = self._generic_action_cancel(action_id, g.auth_state)
        return self._action_status_return_to_view_return(action, 200)

    def action_release(self, func: ActionReleaseType) -> Callable[[str], ViewReturn]:
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
            return jsonify(status), 200

        self.add_url_rule(
            "/<string:action_id>/release", func.__name__, wrapper, methods=["POST"],
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
            print(f"Registered action loader '{func.__name__}'")
            self.action_loader_plugin = (func, storage_backend)

        return wrapper

    def _load_action_by_id(self, action_id: str) -> ActionStatus:
        """
        If the actiond_id is not found in the registered action_loader, we
        assume the ActionStatus is non-recoverable.
        """
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
            print(f"Registered action saver '{func.__name__}'")
            self.action_saver_plugin = (func, storage_backend)

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
        else:
            status, status_code = status
        return jsonify(status), status_code
