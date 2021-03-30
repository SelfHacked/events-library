"""Cron tasks for Invoices."""
# pylint: disable=invalid-name

from django.utils import timezone
from django_cron import CronJobBase, Schedule

from .models import EventLog, HandlerLog


class SuccessfulEventLogsRecycling(CronJobBase):
    """Cron job that deletes successful EventLog
    that were created more than 3 days ago"""

    schedule = Schedule(run_every_mins=60 * 24)
    code = f"{__name__}.SuccessfulEventLogsRecycling"

    def do(self):
        """Run task by cron."""
        eight_days_ago = timezone.now() - timezone.timedelta(days=8)

        EventLog.objects.filter(
            was_success=True,
            created_at__lte=eight_days_ago,
        ).delete()


class ErrorLogsCleanUp(CronJobBase):
    """Cron job that deletes EventLog and 
    HandlerLog that were created over a month ago"""

    schedule = Schedule(run_every_mins=60 * 24)
    code = f"{__name__}.ErrorLogsCleanUp"

    def do(self):
        """Run task by cron."""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

        EventLog.objects.filter(created_at__lte=thirty_days_ago).delete()
        HandlerLog.objects.filter(created_at__lte=thirty_days_ago).delete()
