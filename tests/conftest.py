"""Pytest fixtures for FatSecret MCP Server tests."""

import pytest

from fatsecret_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Return a Settings object with test credentials.

    Returns:
        Settings object configured with test OAuth1 credentials.
    """
    return Settings(
        consumer_key="test_consumer_key",
        consumer_secret="test_consumer_secret",
        api_base_url="https://platform.fatsecret.com/rest/server.api",
    )


@pytest.fixture
def mock_food_response() -> dict:
    """Return a mock food.get API response.

    Returns:
        Dictionary representing a successful food.get response.
    """
    return {
        "food": {
            "food_id": "33691",
            "food_name": "Banana",
            "food_type": "Generic",
            "food_url": "https://www.fatsecret.com/calories-nutrition/generic/banana",
            "food_description": "Per 100g - Calories: 89kcal | Fat: 0.33g | Carbs: 22.84g | Protein: 1.09g",
            "servings": {
                "serving": [
                    {
                        "serving_id": "27445",
                        "serving_description": '1 small (6" to 6-7/8" long)',
                        "metric_serving_amount": "101.000",
                        "metric_serving_unit": "g",
                        "number_of_units": "1.000",
                        "measurement_description": 'small (6" to 6-7/8" long)',
                        "calories": "90",
                        "fat": "0.33",
                        "saturated_fat": "0.112",
                        "polyunsaturated_fat": "0.073",
                        "monounsaturated_fat": "0.032",
                        "trans_fat": "0.000",
                        "cholesterol": "0",
                        "sodium": "1",
                        "potassium": "358",
                        "carbohydrate": "23.07",
                        "fiber": "2.6",
                        "sugar": "12.23",
                        "protein": "1.10",
                        "vitamin_a": "1.28",
                        "vitamin_c": "17.4",
                        "calcium": "5.05",
                        "iron": "0.26",
                    },
                    {
                        "serving_id": "27446",
                        "serving_description": '1 medium (7" to 7-7/8" long)',
                        "metric_serving_amount": "118.000",
                        "metric_serving_unit": "g",
                        "number_of_units": "1.000",
                        "measurement_description": 'medium (7" to 7-7/8" long)',
                        "calories": "105",
                        "fat": "0.39",
                        "saturated_fat": "0.132",
                        "polyunsaturated_fat": "0.086",
                        "monounsaturated_fat": "0.038",
                        "trans_fat": "0.000",
                        "cholesterol": "0",
                        "sodium": "1",
                        "potassium": "422",
                        "carbohydrate": "26.95",
                        "fiber": "3.1",
                        "sugar": "14.43",
                        "protein": "1.29",
                        "vitamin_a": "1.51",
                        "vitamin_c": "20.5",
                        "calcium": "5.90",
                        "iron": "0.31",
                    },
                ]
            },
        }
    }


@pytest.fixture
def mock_search_response() -> dict:
    """Return a mock foods.search API response.

    Returns:
        Dictionary representing a successful foods.search response.
    """
    return {
        "foods": {
            "max_results": "50",
            "page_number": "0",
            "total_results": "3",
            "food": [
                {
                    "food_id": "33691",
                    "food_name": "Banana",
                    "food_type": "Generic",
                    "food_description": "Per 100g - Calories: 89kcal | Fat: 0.33g | Carbs: 22.84g | Protein: 1.09g",
                },
                {
                    "food_id": "424791",
                    "food_name": "Banana Bread",
                    "brand_name": "Generic",
                    "food_type": "Generic",
                    "food_description": "Per 1 slice - Calories: 196kcal | Fat: 6.14g | Carbs: 32.75g | Protein: 3.27g",
                },
                {
                    "food_id": "2183471",
                    "food_name": "Banana Chips",
                    "brand_name": "Generic",
                    "food_type": "Generic",
                    "food_description": "Per 1 oz - Calories: 147kcal | Fat: 9.52g | Carbs: 16.62g | Protein: 0.68g",
                },
            ],
        }
    }


@pytest.fixture
def mock_food_not_found_response() -> dict:
    """Return a mock API error response for food not found.

    Returns:
        Dictionary representing a FatSecret API error 106 (food not found).
    """
    return {
        "error": {
            "code": 106,
            "message": "Invalid food_id",
        }
    }


@pytest.fixture
def mock_barcode_success_response() -> dict:
    """Return a mock successful barcode lookup response.

    Returns:
        Dictionary representing a successful food.find_id_for_barcode response.
    """
    return {
        "food_id": {
            "value": "123456",
        }
    }


@pytest.fixture
def mock_barcode_not_found_response() -> dict:
    """Return a mock barcode not found response.

    Returns:
        Dictionary representing a barcode not found error.
    """
    return {
        "error": {
            "code": 110,
            "message": "Barcode not found",
        }
    }


@pytest.fixture
def mock_recipe_response() -> dict:
    """Return a mock recipe.get API response.

    Returns:
        Dictionary representing a successful recipe.get response.
    """
    return {
        "recipe": {
            "recipe_id": "12345",
            "recipe_name": "Chocolate Chip Cookies",
            "recipe_description": "Delicious homemade chocolate chip cookies",
            "recipe_url": "https://www.fatsecret.com/recipes/chocolate-chip-cookies",
            "preparation_time_min": "15",
            "cooking_time_min": "12",
            "number_of_servings": "24",
            "rating": "4.5",
            "ingredients": {
                "ingredient": [
                    {
                        "food_id": "1001",
                        "food_name": "Butter",
                        "ingredient_description": "1 cup softened butter",
                        "number_of_units": "1.000",
                        "measurement_description": "cup",
                    },
                    {
                        "food_id": "1002",
                        "food_name": "Sugar",
                        "ingredient_description": "1 cup white sugar",
                        "number_of_units": "1.000",
                        "measurement_description": "cup",
                    },
                ]
            },
            "directions": {
                "direction": [
                    {
                        "direction_description": "Preheat oven to 375°F",
                        "direction_number": "1",
                    },
                    {
                        "direction_description": "Mix butter and sugar until creamy",
                        "direction_number": "2",
                    },
                ]
            },
            "serving_sizes": {
                "serving": {
                    "calories": "120",
                    "fat": "6.0",
                    "carbohydrate": "15.0",
                    "protein": "2.0",
                }
            },
        }
    }


@pytest.fixture
def mock_recipes_search_response() -> dict:
    """Return a mock recipes.search API response.

    Returns:
        Dictionary representing a successful recipes.search response.
    """
    return {
        "recipes": {
            "max_results": "20",
            "page_number": "0",
            "total_results": "2",
            "recipe": [
                {
                    "recipe_id": "12345",
                    "recipe_name": "Chocolate Chip Cookies",
                    "recipe_description": "Delicious homemade chocolate chip cookies",
                    "recipe_url": "https://www.fatsecret.com/recipes/chocolate-chip-cookies",
                    "number_of_servings": "24",
                    "rating": "4.5",
                },
                {
                    "recipe_id": "67890",
                    "recipe_name": "Oatmeal Cookies",
                    "recipe_description": "Healthy oatmeal cookies",
                    "recipe_url": "https://www.fatsecret.com/recipes/oatmeal-cookies",
                    "number_of_servings": "18",
                    "rating": "4.2",
                },
            ],
        }
    }
