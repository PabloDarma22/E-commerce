from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class CustomerProfile(models.Model):
    """
    Perfil do cliente (dados extras além do User do Django).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(blank=True, null=True)

    def __str__(self) -> str:
        return f"Perfil de {self.user}"


class Address(models.Model):
    """
    Endereço salvo do cliente (um cliente pode ter vários).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    cep = models.CharField(max_length=9)  # ex: 12345-678
    street = models.CharField(max_length=200)
    number = models.CharField(max_length=20)
    complement = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)  # bairro
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)  # UF

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self) -> str:
        return f"{self.street}, {self.number} - {self.city}/{self.state}"


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    stock = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    # opcionais úteis
    sku = models.CharField(max_length=60, blank=True, unique=True, null=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        CONVERTED = "converted", "Convertido"
        ABANDONED = "abandoned", "Abandonado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
        null=True,
        blank=True,
        help_text="Pode ser null para suportar carrinho de visitante no futuro.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Carrinho #{self.id} - {self.status}"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "Product",  # ou Product, se já estiver acima
        on_delete=models.PROTECT,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} x{self.quantity} (Carrinho #{self.cart_id})"


#Pedido
class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        SHIPPED = "shipped", "Enviado"
        DELIVERED = "delivered", "Entregue"
        CANCELED = "canceled", "Cancelado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # total pode ser derivado dos itens; ainda assim é útil persistir (performance / histórico)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    cart = models.OneToOneField(
    Cart,
    on_delete=models.SET_NULL,
    related_name="order",
    null=True,
    blank=True,
    help_text="Carrinho que originou este pedido (opcional).",
    )

    # snapshot do endereço de entrega (produto físico)
    shipping_cep = models.CharField(max_length=9)
    shipping_street = models.CharField(max_length=200)
    shipping_number = models.CharField(max_length=20)
    shipping_complement = models.CharField(max_length=100, blank=True)
    shipping_district = models.CharField(max_length=100)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Pedido #{self.id} - {self.user} - {self.status}"

    @classmethod
    def from_address(cls, *, user, address: Address, **kwargs):
        """
        Helper para criar pedido já copiando o endereço (snapshot).
        """
        return cls(
            user=user,
            shipping_cep=address.cep,
            shipping_street=address.street,
            shipping_number=address.number,
            shipping_complement=address.complement,
            shipping_district=address.district,
            shipping_city=address.city,
            shipping_state=address.state,
            **kwargs,
        )

    def recalc_total(self, save: bool = True) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.subtotal
        self.total = total
        if save:
            self.save(update_fields=["total", "updated_at"])
        return total


#Item do Pedido
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_product_per_order",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} x{self.quantity} (Pedido #{self.order_id})"

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price or Decimal("0.00")) * self.quantity


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        FAILED = "failed", "Falhou"
        REFUNDED = "refunded", "Estornado"

    class Method(models.TextChoices):
        PIX = "pix", "PIX"
        CARD = "card", "Cartão"
        BOLETO = "boleto", "Boleto"

    # Para MVP, 1 pagamento por pedido costuma bastar.
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    method = models.CharField(
        max_length=20,
        choices=Method.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    transaction_id = models.CharField(max_length=120, blank=True)  # gateway externo (opcional)
    paid_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Pagamento do Pedido #{self.order_id} - {self.status}"
