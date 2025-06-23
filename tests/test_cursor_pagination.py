from django.test import Client
from django.urls import reverse
import pytest
from test_app.models import Category


@pytest.fixture
def categories() -> list[Category]:
    return [Category.objects.create(title=title) for title in ["C", "E", "B", "D", "A"]]


@pytest.fixture
def duplicate_categories() -> list[Category]:
    return [Category.objects.create(title=title) for title in ["A", "B", "B", "B", "C"]]


@pytest.mark.django_db
def test_cursor_pagination_single_page(client: Client, categories: list[Category]) -> None:
    response = client.get(reverse("api-1.0.0:list_categories"))

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {"title": "A"},
            {"title": "B"},
            {"title": "C"},
            {"title": "D"},
            {"title": "E"},
        ],
        "count": 5,
        "next": None,
        "previous": None,
    }


@pytest.mark.django_db
def test_cursor_pagination_iteration_base(client: Client, categories: list[Category]) -> None:
    response = client.get(reverse("api-1.0.0:list_categories"), data={"limit": 2})

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["results"] == [{"title": "A"}, {"title": "B"}]
    assert response_json["count"] == 5
    assert response_json["next"] is not None
    assert response_json["previous"] is None


@pytest.mark.django_db
def test_cursor_pagination_iteration_next(client: Client, categories: list[Category]) -> None:
    response_base = client.get(reverse("api-1.0.0:list_categories"), data={"limit": 2})
    response_next = client.get(response_base.json()["next"])

    assert response_next.status_code == 200
    response_next_json = response_next.json()
    assert response_next_json["results"] == [{"title": "C"}, {"title": "D"}]
    assert response_next_json["count"] == 5
    assert response_next_json["next"] is not None
    assert response_next_json["previous"] is not None


@pytest.mark.django_db
def test_cursor_pagination_iteration_previous(client: Client, categories: list[Category]) -> None:
    response_base = client.get(reverse("api-1.0.0:list_categories"), data={"limit": 2})
    response_next = client.get(response_base.json()["next"])
    response_previous = client.get(response_next.json()["previous"])

    assert response_previous.status_code == 200
    response_previous_json = response_previous.json()
    assert response_previous_json["results"] == [{"title": "A"}, {"title": "B"}]
    assert response_previous_json["count"] == 5
    assert response_previous_json["next"] is not None
    assert response_previous_json["previous"] is None


def test_invalid_cursor(client: Client) -> None:
    response = client.get(reverse("api-1.0.0:list_categories"), data={"cursor": "invalid"})

    assert response.status_code == 422
    assert "Invalid cursor." in response.json()["detail"][0]["msg"]


@pytest.mark.django_db
def test_cursor_pagination_duplicates(client: Client, duplicate_categories: list[Category]) -> None:
    # test cursors that require offsets for duplicate values
    response = client.get(reverse("api-1.0.0:list_categories"), data={"limit": 2})
    assert response.status_code == 200
    assert response.json()["results"] == [{"title": "A"}, {"title": "B"}]

    response = client.get(response.json()["next"])
    assert response.status_code == 200
    assert response.json()["results"] == [{"title": "B"}, {"title": "B"}]

    response = client.get(response.json()["next"])
    assert response.status_code == 200
    assert response.json()["results"] == [{"title": "C"}]
    assert response.json()["next"] is None

    response = client.get(response.json()["previous"])
    assert response.status_code == 200
    assert response.json()["results"] == [{"title": "B"}, {"title": "B"}]
    assert response.json()["next"] is not None
