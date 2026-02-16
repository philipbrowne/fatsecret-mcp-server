"""Tests for FatSecret API client module."""

import asyncio

import pytest
import respx
from httpx import Response

from fatsecret_mcp.api_client import FatSecretClient
from fatsecret_mcp.exceptions import (
    APIError,
    BarcodeNotFoundError,
    FoodNotFoundError,
)
from fatsecret_mcp.models import (
    Food,
    FoodSearchItem,
    FoodSearchResult,
    Recipe,
    RecipeSearchResult,
)


@pytest.mark.asyncio
async def test_search_foods_returns_food_search_result(settings, mock_search_response):
    """Test search_foods returns FoodSearchResult with food items."""
    with respx.mock:
        api_route = respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_search_response)
        )

        client = FatSecretClient(settings)
        result = await client.search_foods("banana")

        assert isinstance(result, FoodSearchResult)
        assert len(result.foods) == 3
        assert result.total_results == 3
        assert result.max_results == 50
        assert result.page_number == 0

        # Verify first food item
        first_food = result.foods[0]
        assert isinstance(first_food, FoodSearchItem)
        assert first_food.food_id == "33691"
        assert first_food.food_name == "Banana"
        assert first_food.food_type == "Generic"

        # Verify API was called
        assert api_route.called


@pytest.mark.asyncio
async def test_search_foods_with_pagination(settings):
    """Test search_foods with page_number and max_results parameters."""
    paginated_response = {
        "foods": {
            "max_results": "10",
            "page_number": "1",
            "total_results": "25",
            "food": [
                {
                    "food_id": "424791",
                    "food_name": "Banana Bread",
                    "brand_name": "Generic",
                    "food_type": "Generic",
                    "food_description": "Per 1 slice - Calories: 196kcal",
                },
            ],
        }
    }

    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=paginated_response)
        )

        client = FatSecretClient(settings)
        result = await client.search_foods("banana", page_number=1, max_results=10)

        assert result.page_number == 1
        assert result.max_results == 10
        assert result.total_results == 25
        assert len(result.foods) == 1


@pytest.mark.asyncio
async def test_get_food_returns_food(settings, mock_food_response):
    """Test get_food returns Food object with servings."""
    with respx.mock:
        api_route = respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_food_response)
        )

        client = FatSecretClient(settings)
        food = await client.get_food("33691")

        assert isinstance(food, Food)
        assert food.food_id == "33691"
        assert food.food_name == "Banana"
        assert food.food_type == "Generic"
        assert len(food.servings) == 2

        # Verify first serving
        serving = food.servings[0]
        assert serving.serving_id == "27445"
        assert serving.serving_description == '1 small (6" to 6-7/8" long)'
        assert serving.calories == 90.0
        assert serving.carbohydrate == 23.07
        assert serving.protein == 1.10

        assert api_route.called


@pytest.mark.asyncio
async def test_get_food_raises_food_not_found_error(
    settings, mock_food_not_found_response
):
    """Test get_food raises FoodNotFoundError on error code 106."""
    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_food_not_found_response)
        )

        client = FatSecretClient(settings)

        with pytest.raises(FoodNotFoundError) as exc_info:
            await client.get_food("invalid_id")

        assert exc_info.value.error_code == 106
        err_str = str(exc_info.value)
        assert "Invalid food_id" in err_str or "not found" in err_str.lower()


@pytest.mark.asyncio
async def test_find_food_by_barcode_success(
    settings, mock_barcode_success_response, mock_food_response
):
    """Test find_food_by_barcode returns Food object on success."""
    with respx.mock:
        # First call returns barcode lookup result, second returns food details
        api_route = respx.post(settings.api_base_url)
        api_route.side_effect = [
            Response(200, json=mock_barcode_success_response),
            Response(200, json=mock_food_response),
        ]

        client = FatSecretClient(settings)
        food = await client.find_food_by_barcode("012345678901")

        # Should return Food object (after calling get_food with the food_id)
        assert isinstance(food, Food)
        assert food.food_name == "Banana"
        assert api_route.call_count == 2


@pytest.mark.asyncio
async def test_find_food_by_barcode_raises_barcode_not_found_error(
    settings, mock_barcode_not_found_response
):
    """Test find_food_by_barcode raises BarcodeNotFoundError when not found."""
    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_barcode_not_found_response)
        )

        client = FatSecretClient(settings)

        with pytest.raises(BarcodeNotFoundError) as exc_info:
            await client.find_food_by_barcode("999999999999")

        assert exc_info.value.error_code in (106, 110)
        assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_recipe_returns_recipe(settings, mock_recipe_response):
    """Test get_recipe returns Recipe object."""
    with respx.mock:
        api_route = respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_recipe_response)
        )

        client = FatSecretClient(settings)
        recipe = await client.get_recipe("12345")

        assert isinstance(recipe, Recipe)
        assert recipe.recipe_id == "12345"
        assert recipe.recipe_name == "Chocolate Chip Cookies"
        assert recipe.preparation_time_min == 15
        assert recipe.cooking_time_min == 12
        assert recipe.number_of_servings == 24
        assert recipe.rating == 4.5

        assert len(recipe.ingredients) == 2
        assert len(recipe.directions) == 2

        assert api_route.called


@pytest.mark.asyncio
async def test_search_recipes_returns_recipe_search_result(
    settings, mock_recipes_search_response
):
    """Test search_recipes returns RecipeSearchResult."""
    with respx.mock:
        api_route = respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_recipes_search_response)
        )

        client = FatSecretClient(settings)
        result = await client.search_recipes("cookies")

        assert isinstance(result, RecipeSearchResult)
        assert len(result.recipes) == 2
        assert result.total_results == 2
        assert result.max_results == 20
        assert result.page_number == 0

        first_recipe = result.recipes[0]
        assert first_recipe.recipe_id == "12345"
        assert first_recipe.recipe_name == "Chocolate Chip Cookies"

        assert api_route.called


@pytest.mark.asyncio
async def test_api_error_handling_general(settings):
    """Test general API error handling."""
    error_response = {
        "error": {
            "code": 2,
            "message": "Missing required parameter",
        }
    }

    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=error_response)
        )

        client = FatSecretClient(settings)

        with pytest.raises(APIError) as exc_info:
            await client.search_foods("")

        assert exc_info.value.error_code == 2


@pytest.mark.asyncio
async def test_http_error_handling(settings):
    """Test handling of HTTP errors (500, 503, etc.)."""
    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(500, text="Internal Server Error")
        )

        client = FatSecretClient(settings)

        with pytest.raises(Exception):  # Could be APIError or HTTPError
            await client.search_foods("test")


@pytest.mark.asyncio
async def test_empty_search_results(settings):
    """Test handling of empty search results."""
    empty_response = {
        "foods": {
            "max_results": "50",
            "page_number": "0",
            "total_results": "0",
        }
    }

    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=empty_response)
        )

        client = FatSecretClient(settings)
        result = await client.search_foods("nonexistentfood12345")

        assert isinstance(result, FoodSearchResult)
        assert len(result.foods) == 0
        assert result.total_results == 0


@pytest.mark.asyncio
async def test_api_client_uses_oauth1_signature(settings, mock_search_response):
    """Test that API client includes OAuth1 signature in requests."""
    with respx.mock:
        api_route = respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_search_response)
        )

        client = FatSecretClient(settings)
        await client.search_foods("test")

        # Verify API call includes OAuth parameters in form data
        assert api_route.called
        api_request = api_route.calls[0].request
        content = api_request.content.decode("utf-8")

        # Check for OAuth1 parameters
        assert "oauth_consumer_key" in content
        assert "oauth_signature" in content
        assert "oauth_signature_method" in content
        assert "oauth_timestamp" in content
        assert "oauth_nonce" in content


@pytest.mark.asyncio
async def test_concurrent_api_requests(settings, mock_search_response):
    """Test that concurrent API requests work correctly."""
    with respx.mock:
        respx.post(settings.api_base_url).mock(
            return_value=Response(200, json=mock_search_response)
        )

        client = FatSecretClient(settings)

        # Make multiple concurrent requests
        results = await asyncio.gather(
            client.search_foods("banana"),
            client.search_foods("apple"),
            client.search_foods("orange"),
        )

        # All should succeed
        assert all(isinstance(r, FoodSearchResult) for r in results)
        assert len(results) == 3
