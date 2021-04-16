import time
import typing

from django.conf import settings
from django.db.models import Model
from django.db.models.signals import post_save, post_delete
from enumfields.drf import EnumSupportSerializerMixin
from rest_framework.serializers import ModelSerializer

from ..core import EventApi
from ..domain import EventLog, HandlerLog, ObjectModel


class CudEvent():
    """A class that encapsulates the available cud events
    as members of the class, to be used instead of raw string"""
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'


class EventBus():
    """Main class of the lib, controlling the
    event's logic and subscription/emittion flow"""

    # A mapping, where the key is an event_type,
    # and the value is a list of event_handlers
    map_event_to_handlers = {}

    # A mapping, where the key is an event_type,
    # and the value is a list of service's names
    map_event_to_target_services = {}

    # A mapping, where the key is the name of a
    # resource ('users', 'articles', 'categories')
    # and the value is a Django Model class, that
    # must inherit from
    map_event_to_model_class = {}

    @classmethod
    def subscribe(cls, event_type: str, event_handler: typing.Callable) -> None:
        """Adds the event_handler to the list of functions to be
        called when an event with the given event_type is emitted"""
        # Get current list of handlers
        event_handlers = cls.map_event_to_handlers.get(event_type, [])

        # Add the new handler
        event_handlers.append(event_handler)
        cls.map_event_to_handlers[event_type] = event_handlers

    @classmethod
    def subscribe_to_cud(
        cls,
        resource_name: str,
        object_model_class: typing.Type[ObjectModel],
    ) -> None:
        """Subscribes a Model class, identified by the given
        resource_name argument, to CUD changes in the service
        which acts as source of true for the given Model"""
        cls.map_event_to_model_class[resource_name] = object_model_class

    @classmethod
    def emit_locally(cls, event_type: str, payload: typing.Dict) -> None:
        """Calls, with the given payload as argument, each
        event_handler that was attached to the given event_type.
        It creates a HandlerLog in case of Exception during the
        execution of a handler funtion"""
        if event_type not in cls.map_event_to_handlers:
            return  # No op

        for event_handler in cls.map_event_to_handlers[event_type]:
            try:
                event_handler(payload)

            except Exception as error:
                # Store exception locally for tracing bugs
                HandlerLog.objects.create(
                    event_type=event_type,
                    payload=payload,
                    error_message=str(error),
                    handler_name=event_handler.__name__,
                )

                # Still raise exception so that the service
                # that sent the event gets notified of the error
                raise error

    @classmethod
    def emit_cud_locally(cls, resource_name: str, payload: typing.Dict) -> None:
        """Performs a CUD action in the Model class that was previously
        subscribed to CUD changes using the same resource_name"""
        model_class: Model = cls.map_event_to_model_class.get(
            resource_name, None
        )
        if not model_class:
            # In case the service is subscribed to
            # the CUD event using an event handler
            cls.emit_locally(resource_name, payload)
            return

        # Remove field that's not part of the ObjectModel class
        object_id = payload['id']
        cud_operation = payload.pop('cud_operation')

        if cud_operation == CudEvent.DELETED:
            model_class.objects.filter(pk=object_id).delete()
        else:
            try:
                model_instance: ObjectModel = model_class.objects.get(
                    pk=object_id,
                )
            except model_class.DoesNotExist:
                model_instance: ObjectModel = model_class(pk=object_id)

            # This is the way that DRF uses for updating models
            for attr, value in payload.items():
                setattr(model_instance, attr, value)

            model_instance.save()

    @classmethod
    def emit_abroad(cls, event_type: str, payload: typing.Dict) -> None:
        """Sends the event to the services that are subscribed to 
        the given event_type, and stores a summary in the EventLog table"""
        if settings.DISABLE_EMIT_IN_EVENTS_LIBRARY:
            return   # No op

        if event_type not in cls.map_event_to_target_services:
            return  # No op

        api = EventApi()
        for target_service in cls.map_event_to_target_services[event_type]:
            event_request_summary = api.send_event_request(
                target_service, event_type, payload,
            )
            it_failed = not event_request_summary["was_success"]

            if it_failed or settings.LOG_EVENTS_ON_SUCCESS:
                EventLog.objects.create(
                    **event_request_summary,
                    payload=payload,
                    event_type=event_type,
                    target_service=target_service,
                )

    @classmethod
    def declare_event(
        cls,
        event_type: str,
        target_services: typing.List[str]
    ):
        """Registers the services that should receive
        the events with the given event_type"""
        current_targets = cls.map_event_to_target_services.get(event_type, [])

        for service_name in target_services:
            if service_name not in current_targets:
                current_targets.append(service_name)

        cls.map_event_to_target_services[event_type] = current_targets

    @classmethod
    def declare_cud_event(
        cls,
        resource_name: str,
        model_class: typing.Type[Model],
        target_services: typing.List[str],
    ):
        """Attachs to the model_class post_save and post_delete signals,
        which emits the appropiate CUD event to the target_services argument"""
        class CustomSerializer(EnumSupportSerializerMixin, ModelSerializer):
            """Serializer that extends ModelSerializer to support EnumFields"""
            class Meta:
                model = model_class
                fields = '__all__'

        def handle_operation(instance, operation: str):
            cud_payload = {
                'id': instance.id,
                'cud_operation': operation,
                'data': CustomSerializer(instance).data,
                'timestamp': time.time(),
            }

            cls.emit_abroad(resource_name, cud_payload)

        def handle_deleted(instance, **kwargs):
            handle_operation(instance, CudEvent.DELETED)

        def handle_edited(instance, created, **kwargs):
            cud_operation = CudEvent.CREATED if created else CudEvent.UPDATED
            handle_operation(instance, cud_operation)

        cls.map_event_to_target_services[resource_name] = target_services
        post_save.connect(handle_edited, sender=model_class, weak=False)
        post_delete.connect(handle_deleted, sender=model_class, weak=False)
