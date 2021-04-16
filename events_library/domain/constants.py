
class CudEvent():
    """A class that encapsulates the available cud events
    as members of the class, to be used instead of raw string"""
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'


class Service():
    """A class that encapsulates the available services
    as members of the class, to be used instead of raw string"""
    ACCOUNTS = 'accounts'
    GENOME_FILES = 'genome-files'
    ORDERS = 'orders'
    PAYMENTS = 'payments'
    PROFILES = 'profiles'
    REGIMENS = 'regimens'
    REPORTS = 'reports'
    SELFDECODE = 'selfdecode'

    @classmethod
    def is_valid(cls, service_name: str):
        return service_name in [
            Service.ACCOUNTS,
            Service.GENOME_FILES,
            Service.ORDERS,
            Service.PAYMENTS,
            Service.PROFILES,
            Service.REGIMENS,
            Service.REPORTS,
            Service.SELFDECODE,
        ]
