import typing

from django.db.models import Model
from typing import Callable, Union

from .application import CudPayloadSerializer  # noqa: F401
from .core import EventBus
from .domain import ObjectModel
from .domain.constants import Service, CudEvent  # noqa: F401


def emit(event_type: str, payload: typing.Dict) -> None:
    """Sends the payload to the services
    that are subscribed to that event_type

    Arguments:
        event_type: str
            The type of the event that will be emitted
        payload: dict
            The data sent along the event
    """
    EventBus.emit_abroad(event_type, payload)


def subscribe_to(
    event_type: str,
    event_handler: Union[Callable, typing.List[Callable]],
) -> None:
    """Performs the required configuration so that when an
    event with the given event_type is emitted, the event_handler
    functions are call using the payload of the event as argument

    Arguments:
        event_type: str
            The type of the event that you want to subscribe to

        event_handler: list | Callable
            The function or list of functions that should
            be called when the event is emitted. The functions
            should receive a single argument: the payload, which
            is a dict object
    """
    if isinstance(event_handler, list):
        for handler in event_handler:
            EventBus.subscribe(event_type, handler)
    else:
        EventBus.subscribe(event_type, event_handler)


def subscribe_to_cud(
    resource_name: str,
    object_model_class: typing.Type[ObjectModel],
) -> None:
    """Subscribes to CUD changes, and reflects them
    in the given object_model_class

    Arguments:
        resource_name: str
            The name of the resource/model ('users', 'articles')

        object_model_class: events_library.models.ObjectModel
            This must be a class that simply inherits from the
            ObjectModel class exported from the events_library
    """
    if not issubclass(object_model_class, ObjectModel):
        raise ValueError(
            f'{object_model_class} does not inherit from '
            'the ObjectModel exported from the events_library'
        )

    EventBus.subscribe_to_cud(resource_name, object_model_class)


def declare_event(
    event_type: str,
    subscribed_services: typing.List[str],
) -> None:
    """Configures that events of the given event_type
    reach the services provided in the subscribed_services
    argument (even if they didn't subscribed to the event).
    NOTE: This function should not be called more than once
    for each event_type: you might be doing something wrong

    Arguments:
        event_type: str
            The type of the event that you want to subscribe to

        subscribed_services: List[str]
            The names of the services that are subscribed to that
            event_type.

    NOTE:
    Admisable values for the service names are:

    - 'accounts'
    - 'orders'
    - 'payments'
    - 'profiles'
    - 'reports'
    - 'selfdecode'

    You can use the Service class (exported from the events_library
    as well) for getting those options and avoid errors
    """
    for service_name in subscribed_services:
        if not Service.is_valid(service_name):
            raise ValueError(
                f'{service_name} is not allowed '
                'as a member of subscribed_services'
            )

    EventBus.declare_event(event_type, subscribed_services)


def declare_cud_event(
    resource_name: str,
    model_class: typing.Type[Model],
    subscribed_services: typing.List[str],
) -> None:
    """Configures a Django Model to send an event (using the resource_name
    argument as event_type) whenever an instance of that model is created,
    updated or deleted, attaching some extra metadata to the event payload

    Arguments:
        resource_name: str
            A name or identifier of the Model ('users', 'articles')

        model_class: django.db.models.Model
            The class of the Model of which you want
            emit events on changes

        subscribed_services: List[str]
            The names of the services that are subscribed
            to changes of the provided model_class

    NOTE:
    Admisable values for the service names are:

    - 'accounts'
    - 'orders'
    - 'payments'
    - 'profiles'
    - 'reports'
    - 'selfdecode'

    You can use the Service class (exported from the events_library
    as well) for getting those options and avoid errors
    """
    for service_name in subscribed_services:
        if not Service.is_valid(service_name):
            raise ValueError(
                f'{service_name} is not allowed '
                'as a member of subscribed_services'
            )

    EventBus.declare_cud_event(resource_name, model_class, subscribed_services)
