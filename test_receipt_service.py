from receipt_service import CheckoutRequest, OrderService


class FakeMailer:
    def send_email(self, to: str, subject: str, html: str):
        return {"message_id": "msg_test"}


def test_hard_bounce_suppresses_future_receipt():
    service = OrderService(FakeMailer())
    service.record_hard_bounce("buyer@example.com")
    result = service.checkout(CheckoutRequest("ord-7", "buyer@example.com", 1299))
    assert result == {"order_id": "ord-7", "email_status": "suppressed"}
