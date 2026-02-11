from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib import messages 
from django.views.generic import ListView, DetailView
from .forms import SignUpForm, AddressForm
from .models import Product, Address, Order, Payment
from django.views.decorators.http import require_POST 
from .services.cart import add_to_cart, get_or_create_active_cart, cart_summary, remove_cart_item, update_cart_item_quantity
from .services.checkout import checkout_cart
from .services.payment import simulate_payment
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin




class HomeView(ListView):
    model = Product
    template_name = "core/home.html"
    context_object_name = "products"
    paginate_by = 12  # quantidade por página

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category").order_by("name")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        return context


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # 1) autentica usuário
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 2) cria sessão
            login(request, user)
            messages.success(request, "Login realizado com sucesso!")
            return redirect("home")
        else:
            messages.error(request, "Usuário ou senha inválidos.")

    return render(request, "auth/login.html")


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # cria o usuário
            login(request, user)  # login automático (recomendado)
            messages.success(request, "Conta criada com sucesso!")
            return redirect("home")
        else:
            messages.error(request, "Corrija os erros abaixo.")
    else:
        form = SignUpForm()

    return render(request, "auth/signup.html", {"form": form})


class ProductDetailView(DetailView):
    model = Product
    template_name = "core/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        # Garante que só produtos ativos podem ser acessados
        return get_object_or_404(Product, slug=self.kwargs["slug"], is_active=True)


@login_required
@require_POST
def add_to_cart_view(request, product_id: int):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    # quantidade vem do form (string) -> int
    qty_str = request.POST.get("quantity", "1").strip()
    try:
        quantity = int(qty_str)
    except ValueError:
        quantity = 1

    # regra mínima: pelo menos 1
    if quantity < 1:
        quantity = 1

    try:
        add_to_cart(user=request.user, product_id=product.id, quantity=quantity)
        messages.success(request, f'"{product.name}" adicionado ao carrinho!')
    except Exception as e:
        # Ideal: tratar exceções específicas do service (ex: sem estoque)
        messages.error(request, f"Não foi possível adicionar ao carrinho: {e}")

    # volta para o detalhe do produto
    return redirect("product_detail", slug=product.slug)


def cart_detail_view(request):
    cart = get_or_create_active_cart(user=request.user)
    summary = cart_summary(cart=cart)
    return render(request, "core/cart_detail.html", {"cart": cart, "summary": summary})


@login_required
@require_POST
def remove_cart_item_view(request, item_id: int):
    try:
        remove_cart_item(user=request.user, item_id=item_id)
        messages.success(request, "Item removido do carrinho.")
    except Exception:
        messages.error(request, "Não foi possível remover o item.")

    return redirect("cart_detail")


@login_required
@require_POST
def update_cart_item_quantity_view(request, item_id: int):
    qty_str = request.POST.get("quantity", "1").strip()
    try:
        quantity = int(qty_str)
    except ValueError:
        quantity = 1

    try:
        updated = update_cart_item_quantity(user=request.user, item_id=item_id, quantity=quantity)
        if updated is None:
            messages.success(request, "Item removido do carrinho.")
        else:
            messages.success(request, "Quantidade atualizada.")
    except Exception as e:
        messages.error(request, f"Não foi possível atualizar a quantidade: {e}")

    return redirect("cart_detail")


@login_required
def checkout_view(request):
    cart = get_or_create_active_cart(user=request.user)
    summary = cart_summary(cart=cart)

    # se carrinho vazio, volta pro carrinho
    if not summary["items"]:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("cart_detail")

    addresses = Address.objects.filter(user=request.user).order_by("-is_default", "-id")

    return render(
        request,
        "core/checkout.html",
        {
            "cart": cart,
            "summary": summary,
            "addresses": addresses,
        },
    )


@login_required
@require_POST
def checkout_confirm_view(request):
    cart = get_or_create_active_cart(user=request.user)
    summary = cart_summary(cart=cart)

    if not summary["items"]:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("cart_detail")

    address_id_str = request.POST.get("address_id", "").strip()
    if not address_id_str.isdigit():
        messages.error(request, "Selecione um endereço válido.")
        return redirect("checkout")

    address_id = int(address_id_str)

    # garante que o endereço pertence ao usuário
    address = get_object_or_404(Address, id=address_id, user=request.user)

    try:
        order = checkout_cart(user=request.user, cart_id=cart.id, address_id=address.id)
        messages.success(request, "Pedido criado com sucesso!")
        return redirect("order_detail", order_id=order.id)
    except Exception as e:
        messages.error(request, f"Não foi possível finalizar a compra: {e}")
        return redirect("checkout")


def order_detail_view(request, order_id: int):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related("product").all()  # se related_name="items"
    return render(request, "core/order_detail.html", {"order": order, "items": items})


@login_required
def address_list_view(request):
    addresses = Address.objects.filter(user=request.user).order_by("-is_default", "-id")
    return render(request, "core/address_list.html", {"addresses": addresses})


@login_required
def address_create_view(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.save()

            # Se marcou como padrão, desmarca os demais
            if addr.is_default:
                Address.objects.filter(user=request.user).exclude(id=addr.id).update(is_default=False)

            messages.success(request, "Endereço cadastrado com sucesso!")
            return redirect("address_list")
    else:
        form = AddressForm()

    return render(request, "core/address_form.html", {"form": form})


@login_required
@require_POST
def address_set_default_view(request, address_id: int):
    addr = get_object_or_404(Address, id=address_id, user=request.user)

    Address.objects.filter(user=request.user).update(is_default=False)
    addr.is_default = True
    addr.save(update_fields=["is_default"])

    messages.success(request, "Endereço padrão atualizado!")
    return redirect("address_list")


@login_required
@require_POST
def address_delete_view(request, address_id: int):
    addr = get_object_or_404(Address, id=address_id, user=request.user)
    addr.delete()
    messages.success(request, "Endereço removido.")
    return redirect("address_list")


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "core/order_list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .order_by("-created_at")
        )



@login_required
@require_POST
def order_pay_view(request, order_id: int):
    method = (request.POST.get("method") or "").strip().lower()

    # Valida o método (pix/card/boleto)
    allowed_methods = {choice[0] for choice in Payment.Method.choices}
    if method not in allowed_methods:
        messages.error(request, "Selecione um método de pagamento válido.")
        return redirect("order_detail", order_id=order_id)

    try:
        simulate_payment(user=request.user, order_id=order_id, method=method)
        messages.success(request, "Pagamento aprovado (simulação)!")
    except Exception as e:
        messages.error(request, f"Não foi possível concluir o pagamento: {e}")

    return redirect("order_detail", order_id=order_id)

