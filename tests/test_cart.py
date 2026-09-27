from unittest.mock import Mock

import pytest
from conftest import FakeRateProvider

from shop.cart import Cart, Item

# --- add / items_count ---


def test_new_cart_is_empty(cart: Cart) -> None:
    assert cart.items_count() == 0
    assert cart.total() == 0


def test_add_single_item_default_qty(cart: Cart) -> None:
    cart.add("apple", 10.0)
    assert cart.items_count() == 1
    assert cart.total() == 10.0


def test_add_same_item_increases_qty(cart: Cart) -> None:
    cart.add("apple", 10.0, 2)
    cart.add("apple", 10.0, 3)
    assert cart.items_count() == 5
    assert cart.total() == 50.0


def test_add_same_name_different_price_raises(cart: Cart) -> None:
    # Рішення: конфлікт ціни — помилка. Інакше друга ціна мовчки губиться
    # (було: apple 10×1 + apple 20×1 -> total 20 замість 30).
    cart.add("apple", 10.0, 1)
    with pytest.raises(ValueError, match="price mismatch"):
        cart.add("apple", 20.0, 1)
    # кошик не змінився після невдалої операції
    assert cart.items_count() == 1
    assert cart.total() == 10.0


def test_add_free_item_zero_price(cart: Cart) -> None:
    cart.add("gift", 0, 1)
    assert cart.items_count() == 1
    assert cart.total() == 0


def test_items_count_multiple_items(filled_cart: Cart) -> None:
    assert filled_cart.items_count() == 5


# --- винятки add ---


@pytest.mark.parametrize("price", [-0.01, -1, -100])
def test_add_negative_price_raises(cart: Cart, price: float) -> None:
    with pytest.raises(ValueError, match="price must be non-negative"):
        cart.add("apple", price)


@pytest.mark.parametrize("qty", [0, -1])
def test_add_non_positive_qty_raises(cart: Cart, qty: int) -> None:
    with pytest.raises(ValueError, match="qty must be positive"):
        cart.add("apple", 10.0, qty)


# --- remove ---


def test_remove_existing_item(filled_cart: Cart) -> None:
    filled_cart.remove("apple")
    assert filled_cart.items_count() == 2
    assert filled_cart.total() == 51.0


def test_remove_missing_item_raises(cart: Cart) -> None:
    with pytest.raises(KeyError):
        cart.remove("ghost")


# --- total зі знижкою: граничні значення ---


@pytest.mark.parametrize(
    ("discount", "expected"),
    [
        (0, 81.0),  # нижня межа
        (0.01, 80.99),  # трохи вище нижньої межі
        (50, 40.5),
        (99.99, 0.01),  # трохи нижче верхньої межі
        (100, 0.0),  # верхня межа
    ],
)
def test_total_discount_boundaries(filled_cart: Cart, discount: float, expected: float) -> None:
    assert filled_cart.total(discount) == expected


@pytest.mark.parametrize("discount", [-0.01, 100.01, -50, 150])
def test_total_invalid_discount_raises(filled_cart: Cart, discount: float) -> None:
    with pytest.raises(ValueError, match="discount_percent"):
        filled_cart.total(discount)


def test_total_is_rounded_to_cents(cart: Cart) -> None:
    cart.add("pen", 0.1, 3)
    assert cart.total() == 0.3


# --- total_in з тестовими дублерами RateProvider ---


def test_total_in_with_mock(filled_cart: Cart) -> None:
    rates = Mock()
    rates.get_rate.return_value = 40.0

    assert filled_cart.total_in("USD", rates) == 2.02  # 81 / 40 = 2.025

    rates.get_rate.assert_called_once_with("USD")


def test_total_in_with_fake_provider(filled_cart: Cart, fake_rates: FakeRateProvider) -> None:
    assert filled_cart.total_in("EUR", fake_rates) == 1.8  # 81 / 45
    assert fake_rates.calls == ["EUR"]


@pytest.mark.parametrize("rate", [0, -1, -0.5])
def test_total_in_invalid_rate_raises(filled_cart: Cart, rate: float) -> None:
    rates = Mock()
    rates.get_rate.return_value = rate
    with pytest.raises(ValueError, match="rate must be positive"):
        filled_cart.total_in("USD", rates)


def test_total_in_propagates_provider_error(filled_cart: Cart) -> None:
    rates = Mock()
    rates.get_rate.side_effect = KeyError("XYZ")
    with pytest.raises(KeyError):
        filled_cart.total_in("XYZ", rates)


# --- most_expensive ---


def test_most_expensive_empty_cart_returns_none(cart: Cart) -> None:
    assert cart.most_expensive() is None


def test_most_expensive_single_item(cart: Cart) -> None:
    cart.add("apple", 10.0, 3)
    assert cart.most_expensive() == Item("apple", 10.0, 3)


def test_most_expensive_by_unit_price_not_line_total(cart: Cart) -> None:
    cart.add("cheap", 1.0, 100)  # сума рядка 100, але ціна одиниці мала
    cart.add("pricey", 50.0, 1)
    result = cart.most_expensive()
    assert result is not None
    assert result.name == "pricey"


def test_most_expensive_tie_returns_first_added(cart: Cart) -> None:
    cart.add("first", 20.0)
    cart.add("second", 20.0)
    result = cart.most_expensive()
    assert result is not None
    assert result.name == "first"


def test_most_expensive_after_remove(filled_cart: Cart) -> None:
    filled_cart.remove("bread")
    result = filled_cart.most_expensive()
    assert result is not None
    assert result.name == "apple"
