import pytest

from shop.cart import Cart


class FakeRateProvider:
    """Тестова заглушка RateProvider з фіксованими курсами, без мережі."""

    def __init__(self, rates: dict[str, float]) -> None:
        self._rates = rates
        self.calls: list[str] = []

    def get_rate(self, currency: str) -> float:
        self.calls.append(currency)
        return self._rates[currency]


@pytest.fixture
def cart() -> Cart:
    return Cart()


@pytest.fixture
def filled_cart() -> Cart:
    c = Cart()
    c.add("apple", 10.0, 3)
    c.add("bread", 25.5, 2)
    return c  # total = 30 + 51 = 81.0


@pytest.fixture
def fake_rates() -> FakeRateProvider:
    return FakeRateProvider({"USD": 40.0, "EUR": 45.0})
