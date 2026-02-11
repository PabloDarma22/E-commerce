from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import Order, Payment


@transaction.atomic
def simulate_payment(user, order_id: int, method: str):
    """
    Simula um pagamento para um pedido:
    - garante que o pedido é do usuário
    - impede pagamento duplicado
    - cria Payment (OneToOne)
    - atualiza status do pedido
    """

    # 1. Busca o pedido do usuário e trava a linha
    order = get_object_or_404(
        Order.objects.select_for_update(),
        id=order_id,
        user=user,
    )

    # 2. Se o pedido já tem pagamento
    if hasattr(order, "payment"):
        payment = order.payment

        if payment.status == Payment.Status.PAID:
            return payment

        if payment.status != Payment.Status.PENDING:
            raise ValueError("Este pedido não pode ser pago no momento.")

    # 3. Pedido precisa estar pendente
    if order.status != Order.Status.PENDING:
        raise ValueError("Este pedido não está pendente para pagamento.")

    # 4. Cria o pagamento (mock)
    payment = Payment.objects.create(
        order=order,
        method=method,
        status=Payment.Status.PAID,
        paid_at=timezone.now(),
        transaction_id="MOCK-" + timezone.now().strftime("%Y%m%d%H%M%S"),
    )

    # 5. Atualiza status do pedido
    order.status = Order.Status.PAID
    order.save(update_fields=["status"])

    return payment
