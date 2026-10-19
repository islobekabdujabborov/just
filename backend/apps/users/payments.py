from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    @abstractmethod
    def create_checkout(self, subscription):
        raise NotImplementedError

    @abstractmethod
    def handle_webhook(self, request):
        raise NotImplementedError
