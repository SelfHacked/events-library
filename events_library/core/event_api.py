"""EventApi class, used for emitting events"""
import typing

from django.conf import settings
from requests import Request, RequestException, Session
from rest_framework.renderers import JSONRenderer

from ..domain import EventLog

LOG_EVENTS_ON_SUCCESS = settings.LOG_EVENTS_ON_SUCCESS


class EventApi:
    """Class for making HTTP request related to events"""

    def __init__(self, domain: str = None, max_retries: int = None) -> None:
        """Initialize requests session."""
        self.session = Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
        })

        self.domain = domain or settings.DOMAIN_NAME
        self.max_retries = max_retries or 1

    def send_request(
        self,
        url: str,
        data: typing.Dict,
        raise_exception: bool = True,
    ):
        """Sends a request to the specified url

        Arguments:
            url: str
                The url of the endpoint
            data: dict
                The data sent in the request
            raise_exception: bool
                Wheter to raise an exception when an
                HTTPError is found while doing the request
        """
        protocol = 'http' if self.domain == 'localhost' else 'https'
        req = Request(
            method='POST',
            url=f'{protocol}://{self.domain}/{url}',
            data=JSONRenderer().render(data),
            headers={
                'Token': settings.JWT_AUTH['SERVICE_SECRET_TOKEN'],
            },
        )

        prepared_req = self.session.prepare_request(req)
        resp = self.session.send(prepared_req)

        if raise_exception:
            resp.raise_for_status()

    def send_event_request(
        self,
        service_name: str,
        event_type: str,
        payload: typing.Dict,
    ) -> dict:
        """Sends event, with retries, to the provided service_name, and
        returns a summary of the proccess (failures, retries, etc.)

        Arguments:
            service_name: str
                The name of the service who will receive the event
            event_type: str
                The type of event being sent
            payload: dict
                The payload data sent along the event        

        Returns:
            event_request_summary: {                    
                was_success: bool
                    Tells if the event was received and handled
                    without errors by the target service
                retry_number: int
                    Amount of times the request was retried before
                    ending up in success or reaching the max_retries
                error_message: str
                    The error message from the exception caught during
                    the last retry of sending the event
            }
        """
        retry_number = 0
        was_success = False
        error_message = 'No errors'
        path = f'service/{service_name}/event/'
        event = {'event_type': event_type, 'payload': payload}

        while (retry_number < self.max_retries):
            try:
                self.send_request(path, event)
                was_success = True

            except RequestException as error:
                retry_number += 1
                error_message = str(error)

            finally:
                if was_success:
                    break

        return {
            "was_success": was_success,
            "retry_number": retry_number,
            "error_message": error_message,
        }
