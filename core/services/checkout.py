from decimal import Decimal
from django.db import transaction
from ..models import Address, Cart, Order, OrderItem, Product


class CheckoutError(Exception):
    pass


class InvalidCartError(CheckoutError):
    pass


class OutOfStockError(CheckoutError):
    pass


@transaction.atomic
def checkout_cart(*, user, cart_id: int, address_id: int) -> Order:
    """
    Converte um carrinho ativo em pedido:
    - valida endereço pertence ao usuário
    - trava produtos (select_for_update)
    - valida estoque definitivo
    - cria Order com snapshot do endereço
    - cria OrderItems com unit_price
    - baixa estoque
    - calcula total
    - marca carrinho como CONVERTED
    """
    # 1) valida endereço
    try:
        address = Address.objects.get(id=address_id, user=user)
    except Address.DoesNotExist:
        raise InvalidCartError("Endereço inválido ou não pertence ao usuário.")

    # 2) pega carrinho
    try:
        cart = Cart.objects.select_for_update().get(id=cart_id, user=user, status=Cart.Status.ACTIVE)
    except Cart.DoesNotExist:
        raise InvalidCartError("Carrinho inválido ou não está ativo.")

    cart_items = list(cart.items.select_related("product").all())
    if not cart_items:
        raise InvalidCartError("Carrinho vazio.")

    product_ids = [it.product_id for it in cart_items]

    # 3) trava os produtos (evita duas compras ao mesmo tempo estourarem estoque)
    products = Product.objects.select_for_update().filter(id__in=product_ids, is_active=True)
    products_by_id = {p.id: p for p in products}

    if len(products_by_id) != len(set(product_ids)):
        raise InvalidCartError("Existe produto inexistente ou inativo no carrinho.")

    # 4) valida estoque definitivo
    for it in cart_items:
        p = products_by_id[it.product_id]
        if p.stock < it.quantity:
            raise OutOfStockError(f"Sem estoque para '{p.name}'. Disponível: {p.stock}")

    # 5) cria pedido com snapshot do endereço
    order = Order.from_address(user=user, address=address)
    order.status = Order.Status.PENDING
    # opcional (se você adicionou o campo cart no Order)
    if hasattr(order, "cart_id"):
        order.cart = cart
    order.save()

    # 6) cria itens do pedido e baixa estoque
    total = Decimal("0.00")
    order_items_to_create = []

    for it in cart_items:
        p = products_by_id[it.product_id]
        unit_price = p.price

        order_items_to_create.append(OrderItem(
            order=order,
            product=p,
            quantity=it.quantity,
            unit_price=unit_price,
        ))

        total += unit_price * it.quantity

        p.stock -= it.quantity
        p.save(update_fields=["stock"])

    OrderItem.objects.bulk_create(order_items_to_create)

    # 7) finaliza total do pedido
    order.total = total
    order.save(update_fields=["total"])

    # 8) marca carrinho como convertido e limpa itens (opcional)
    cart.status = Cart.Status.CONVERTED
    cart.save(update_fields=["status"])
    cart.items.all().delete()

    return order
