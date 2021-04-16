import typing

from django.contrib import admin
from django.db.models import Model, QuerySet
from django.http.request import HttpRequest

from .core import EventApi
from .domain import EventLog, HandlerLog


class InmutableAdminModel(admin.ModelAdmin):
    """Admin model class that disables the
    Add and Edit functionalities of the model,
    although it still allows the deletion"""

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disables Add"""
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: typing.Optional[Model] = None,
    ) -> bool:
        """Disables Edit"""
        return False


@admin.register(EventLog)
class EventLogAdmin(InmutableAdminModel):
    list_filter = [
        "was_success",
        "event_type",
        "target_service",
    ]
    list_display = [
        'id', 'event_type', 'target_service',
        "retry_number", 'was_success', 'created_at',
    ]
    ordering = ["-created_at"]
    actions = ["resend_failed_events"]

    def resend_failed_events(self, request: HttpRequest, queryset: QuerySet[EventLog]) -> None:
        """Resends failed EventLogs selected by the user"""
        api = EventApi()
        fail_count = 0
        total = queryset.count()

        for event_log in queryset.filter(was_success=False):
            event_request_summary = api.send_event_request(
                event_log.target_service,
                event_log.event_type,
                event_log.payload,
            )

            event_log.was_success = event_request_summary["was_success"]
            if not event_log.was_success:
                fail_count += 1
                # Update last error_message only in this case (in case
                # we want to see more common bugs in our service system)
                event_log.error_message = event_request_summary["error_message"]

            # Count all retries since creation of the EventLog
            event_log.retry_number += event_request_summary["retry_number"]
            event_log.save()

        self.message_user(
            request,
            f"Finished resending events: {fail_count} (out of {total}) failed"
        )

    resend_failed_events.short_description = (
        "Mark only failed events: successful ones will be resended"
    )


@admin.register(HandlerLog)
class HandlerLogAdmin(InmutableAdminModel):
    list_filter = ["event_type", "handler_name"]

    list_display = [
        'id', 'event_type',
        'handler_name', 'created_at',
    ]
    ordering = ["-created_at"]
