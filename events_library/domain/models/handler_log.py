from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from .base import BaseModel


class HandlerLog(BaseModel):
    handler_name = models.CharField(max_length=60, blank=False)
    error_message = models.TextField(blank=False)

    event_type = models.CharField(max_length=60, blank=False)
    payload = JSONField(default=dict, encoder=DjangoJSONEncoder)

    def __str__(self):
        return self.event_type
