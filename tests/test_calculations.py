from annika_only_depot import calculate_value
from Annika1 import calculate_portfolio_value


def test_calculate_value_basic():
    portfolio = [
        {"Ticker": "AAA", "Quantity": 10},
        {"Ticker": "BBB", "Quantity": 5},
    ]
    prices = {"AAA": 50, "BBB": 20}
    ownership = {"Percentage": 50}
    result = calculate_value(portfolio, prices, 1000, ownership)
    assert result == 800


def test_calculate_value_ignores_invalid_prices():
    portfolio = [
        {"Ticker": "AAA", "Quantity": 10},
        {"Ticker": "BBB", "Quantity": 5},
    ]
    prices = {"AAA": None, "BBB": 0}
    ownership = {"Percentage": 100}
    result = calculate_value(portfolio, prices, 500, ownership)
    assert result == 500


def test_calculate_portfolio_value_basic():
    portfolio = [
        {"Ticker": "AAA", "Quantity": 2},
        {"Ticker": "BBB", "Quantity": 1},
    ]
    prices = {"AAA": 10, "BBB": 5}
    total, data = calculate_portfolio_value(portfolio, prices, 100)
    assert total == 100 + 2*10 + 1*5
    assert any(item["Ticker"] == "AAA" and item["Value"] == 20 for item in data)
    assert any(item["Ticker"] == "BBB" and item["Value"] == 5 for item in data)
