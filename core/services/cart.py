from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.db.models import F

from ..models import Cart, CartItem, Product
from django.shortcuts import get_object_or_404
from django.db import transaction




class CartError(Exception):
    pass


class ProductUnavailableError(CartError):
    pass


class InvalidQuantityError(CartError):
    pass


@transaction.atomic
def get_or_create_active_cart(*, user) -> Cart:
    """
    Retorna o carrinho ativo do usuário (ou cria um novo).
    Regra: usuário deve ter no máximo 1 carrinho ativo.
    """
    cart = (
        Cart.objects
        .select_for_update()
        .filter(user=user, status=Cart.Status.ACTIVE)
        .order_by("-updated_at")
        .first()
    )
    if cart:
        return cart
    return Cart.objects.create(user=user, status=Cart.Status.ACTIVE)


@transaction.atomic
def add_to_cart(*, user, product_id: int, quantity: int = 1) -> Cart:
    """
    Adiciona um produto ao carrinho ativo.
    Validação leve de estoque (UX). Validação definitiva acontece no checkout.
    """
    if quantity <= 0:
        raise InvalidQuantityError("Quantidade deve ser maior que zero.")

    product = Product.objects.filter(id=product_id, is_active=True).first()
    if not product:
        raise ProductUnavailableError("Produto não encontrado ou inativo.")

    # validação leve (não é a validação final)
    if product.stock < quantity:
        raise ProductUnavailableError(f"Estoque insuficiente. Disponível: {product.stock}")

    cart = get_or_create_active_cart(user=user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity},
    )

    if not created:
        # incrementa quantidade sem condição de corrida
        new_qty = item.quantity + quantity
        if product.stock < new_qty:
            raise ProductUnavailableError(f"Estoque insuficiente. Disponível: {product.stock}")

        CartItem.objects.filter(id=item.id).update(quantity=F("quantity") + quantity)

    # atualiza timestamp do carrinho
    Cart.objects.filter(id=cart.id).update()
    cart.refresh_from_db()
    return cart


@transaction.atomic
def set_item_quantity(*, user, product_id: int, quantity: int) -> Cart:
    """
    Define a quantidade do produto no carrinho (substitui).
    Se quantity == 0, remove item.
    """
    if quantity < 0:
        raise InvalidQuantityError("Quantidade não pode ser negativa.")

    product = Product.objects.filter(id=product_id, is_active=True).first()
    if not product:
        raise ProductUnavailableError("Produto não encontrado ou inativo.")

    cart = get_or_create_active_cart(user=user)

    item = CartItem.objects.filter(cart=cart, product=product).first()
    if not item:
        if quantity == 0:
            return cart
        # cria se não existir
        if product.stock < quantity:
            raise ProductUnavailableError(f"Estoque insuficiente. Disponível: {product.stock}")
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)
        return cart

    if quantity == 0:
        item.delete()
        return cart

    if product.stock < quantity:
        raise ProductUnavailableError(f"Estoque insuficiente. Disponível: {product.stock}")

    CartItem.objects.filter(id=item.id).update(quantity=quantity)
    return cart


@transaction.atomic
def remove_from_cart(*, user, product_id: int) -> Cart:
    cart = get_or_create_active_cart(user=user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    return cart


def cart_summary(*, cart: Cart) -> dict:
    """
    Retorna um resumo calculado do carrinho (não persiste total).
    """
    items = (
        cart.items
        .select_related("product", "product__category")
        .all()
    )

    total = 0
    lines = []

    for it in items:
        product = it.product

        subtotal = product.price * it.quantity
        total += subtotal

        # imagem (se existir)
        image_url = ""
        if getattr(product, "image", None):
            try:
                if product.image:
                    image_url = product.image.url
            except Exception:
                image_url = ""

        lines.append({
            "cart_item_id": it.id,
            "product_id": product.id,
            "slug": getattr(product, "slug", ""),
            "name": product.name,
            "category": product.category.name if getattr(product, "category", None) else "",
            "image_url": image_url,
            "unit_price": product.price,
            "quantity": it.quantity,
            "subtotal": subtotal,
        })

    return {"cart_id": cart.id, "items": lines, "total": total}



def remove_cart_item(user, item_id: int):
    """
    Remove um item do carrinho ativo do usuário.
    """
    cart = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart=cart
    )

    item.delete()


@transaction.atomic
def update_cart_item_quantity(user, item_id: int, quantity: int):
    item = get_object_or_404(
        CartItem.objects.select_related("cart", "product").select_for_update(),
        id=item_id,
        cart__user=user,
        cart__status=Cart.Status.ACTIVE,
    )

    if quantity <= 0:
        item.delete()
        return None

    if not item.product.is_active:
        raise ValueError("Produto indisponível.")

    if quantity > item.product.stock:
        raise ValueError(f"Estoque insuficiente. Disponível: {item.product.stock}")

    item.quantity = quantity
    item.save()  # <-- salva SEM update_fields (mais difícil dar “falso positivo”)
    return item