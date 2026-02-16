"""FatSecret API client implementation."""

from typing import Any

import httpx

from .auth import OAuth1Signer
from .config import Settings
from .exceptions import (
    APIError,
    BarcodeNotFoundError,
    FoodNotFoundError,
    RateLimitError,
    RecipeNotFoundError,
    UserNotAuthenticatedError,
)
from .models import (
    Food,
    FoodDiary,
    FoodEntry,
    FoodEntryServing,
    FoodSearchResult,
    NLPResult,
    Recipe,
    RecipeSearchResult,
    UserToken,
    WeightEntry,
    WeightResult,
)


class FatSecretClient:
    """Client for interacting with the FatSecret API.

    Handles authentication, API requests, and response parsing.
    Supports async context manager protocol.
    """

    def __init__(self, settings: Settings, user_token: UserToken | None = None) -> None:
        """Initialize the FatSecret API client.

        Args:
            settings: Application settings containing API configuration.
            user_token: Optional user token for 3-legged OAuth authentication.
        """
        self._settings = settings
        self._user_token = user_token

        # Create signer with or without user token
        if user_token:
            self._signer = OAuth1Signer(
                settings,
                user_token=user_token.oauth_token,
                user_token_secret=user_token.oauth_token_secret,
            )
        else:
            self._signer = OAuth1Signer(settings)

        self._client = httpx.AsyncClient()

    @property
    def is_user_authenticated(self) -> bool:
        """Check if client has user authentication.

        Returns:
            True if user token is configured, False otherwise.
        """
        return self._user_token is not None

    def _require_user_auth(self) -> None:
        """Raise an error if user authentication is not configured.

        Raises:
            UserNotAuthenticatedError: If no user token is configured.
        """
        if not self.is_user_authenticated:
            raise UserNotAuthenticatedError(
                "This operation requires user authentication. "
                "Please connect your FatSecret account first."
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "FatSecretClient":
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager."""
        await self.close()

    async def _make_request(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a request to the FatSecret API.

        Args:
            method: The API method to call.
            params: Additional parameters for the API call.

        Returns:
            The JSON response from the API.

        Raises:
            APIError: If the API returns an error.
            RateLimitError: If rate limit is exceeded.
        """
        # Build base request parameters
        request_params = {
            "method": method,
            "format": "json",
        }
        # Convert all param values to strings for OAuth signing
        for key, value in params.items():
            request_params[key] = str(value)

        # Sign request with OAuth1
        signed_params = self._signer.sign_request(
            self._settings.api_base_url,
            "POST",
            request_params,
        )

        try:
            response = await self._client.post(
                self._settings.api_base_url,
                data=signed_params,
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors in the response
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                error_code = data["error"].get("code")

                # Handle specific error codes
                if error_code == 9:  # Rate limit exceeded
                    raise RateLimitError(error_msg, error_code)
                elif error_code == 106:  # Food not found
                    raise FoodNotFoundError(error_msg, error_code)
                elif error_code == 107:  # Recipe not found
                    raise RecipeNotFoundError(error_msg, error_code)
                elif error_code == 110:  # Barcode not found
                    raise BarcodeNotFoundError(error_msg, error_code)

                raise APIError(error_msg, error_code)

            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", error_code=9)
            raise APIError(f"HTTP error {e.response.status_code}: {e.response.text}")

        except httpx.RequestError as e:
            raise APIError(f"Request error: {str(e)}")

    async def search_foods(
        self, query: str, page_number: int = 0, max_results: int = 20
    ) -> FoodSearchResult:
        """Search for foods by keyword.

        Args:
            query: The search query.
            page_number: The page number for pagination (0-indexed).
            max_results: Maximum number of results per page.

        Returns:
            Search results containing matching foods.
        """
        params = {
            "search_expression": query,
            "page_number": page_number,
            "max_results": max_results,
        }

        data = await self._make_request("foods.search", params)

        # Parse the response - API returns {"foods": {"food": [...], ...}}
        foods_data = data.get("foods", {})

        # Handle case where no results are found
        if not foods_data or "food" not in foods_data:
            return FoodSearchResult(
                foods=[],
                max_results=max_results,
                total_results=int(foods_data.get("total_results", 0)),
                page_number=page_number,
            )

        # Parse food items
        food_list = foods_data["food"]
        if not isinstance(food_list, list):
            food_list = [food_list]

        from .models import FoodSearchItem

        foods = [FoodSearchItem(**food) for food in food_list]

        return FoodSearchResult(
            foods=foods,
            max_results=int(foods_data.get("max_results", max_results)),
            total_results=int(foods_data.get("total_results", len(foods))),
            page_number=int(foods_data.get("page_number", page_number)),
        )

    async def get_food(self, food_id: int) -> Food:
        """Get detailed information about a specific food.

        Args:
            food_id: The FatSecret food ID.

        Returns:
            Detailed food information including servings.

        Raises:
            FoodNotFoundError: If the food is not found.
        """
        params = {"food_id": food_id}

        try:
            data = await self._make_request("food.get.v4", params)
        except APIError as e:
            if e.error_code == 106:  # Food not found
                raise FoodNotFoundError(f"Food with ID {food_id} not found", 106)
            raise

        # Parse the response
        food_data = data.get("food", {})

        # Handle servings
        servings_data = food_data.get("servings", {}).get("serving", [])
        if not isinstance(servings_data, list):
            servings_data = [servings_data]

        from .models import FoodServing

        food_data["servings"] = [FoodServing(**s) for s in servings_data]

        return Food(**food_data)

    async def find_food_by_barcode(self, barcode: str) -> Food:
        """Look up a food by barcode.

        Args:
            barcode: The product barcode (UPC/EAN).

        Returns:
            Food information for the scanned product.

        Raises:
            BarcodeNotFoundError: If the barcode is not found.
        """
        params = {"barcode": barcode}

        try:
            data = await self._make_request("food.find_id_for_barcode", params)
        except APIError as e:
            if e.error_code == 106:  # Barcode not found
                raise BarcodeNotFoundError(f"Barcode {barcode} not found", 106)
            raise

        # Get food_id from barcode lookup
        food_id_data = data.get("food_id", {})
        food_id = int(food_id_data.get("value", 0))

        if not food_id:
            raise BarcodeNotFoundError(f"Barcode {barcode} not found")

        # Now get the full food details
        return await self.get_food(food_id)

    async def parse_food_description(self, description: str) -> NLPResult:
        """Parse a natural language food description.

        Note: This feature requires OAuth2 authentication with 'nlp' scope.
        It is not available with OAuth1 authentication.

        Args:
            description: Natural language description (e.g., "2 eggs and toast").

        Returns:
            Parsed food items with estimated nutrition.

        Raises:
            APIError: NLP parsing requires OAuth2 authentication.
        """
        raise APIError(
            "Natural Language Processing requires OAuth2 authentication with 'nlp' "
            "scope. This feature is not available with OAuth1.",
            error_code=None,
        )

    async def search_recipes(
        self, query: str, page_number: int = 0, max_results: int = 20
    ) -> RecipeSearchResult:
        """Search for recipes by keyword.

        Args:
            query: The search query.
            page_number: The page number for pagination (0-indexed).
            max_results: Maximum number of results per page.

        Returns:
            Search results containing matching recipes.
        """
        params = {
            "search_expression": query,
            "page_number": page_number,
            "max_results": max_results,
        }

        data = await self._make_request("recipes.search.v3", params)

        # Parse the response - API returns {"recipes": {"recipe": [...], ...}}
        recipes_data = data.get("recipes", {})

        # Handle case where no results are found
        if not recipes_data or "recipe" not in recipes_data:
            return RecipeSearchResult(
                recipes=[],
                max_results=max_results,
                total_results=int(recipes_data.get("total_results", 0)),
                page_number=page_number,
            )

        # Parse recipe items
        recipe_list = recipes_data["recipe"]
        if not isinstance(recipe_list, list):
            recipe_list = [recipe_list]

        from .models import RecipeSearchItem

        recipes = [RecipeSearchItem(**recipe) for recipe in recipe_list]

        return RecipeSearchResult(
            recipes=recipes,
            max_results=int(recipes_data.get("max_results", max_results)),
            total_results=int(recipes_data.get("total_results", len(recipes))),
            page_number=int(recipes_data.get("page_number", page_number)),
        )

    async def get_recipe(self, recipe_id: int) -> Recipe:
        """Get detailed information about a specific recipe.

        Args:
            recipe_id: The FatSecret recipe ID.

        Returns:
            Detailed recipe information including ingredients and directions.

        Raises:
            RecipeNotFoundError: If the recipe is not found.
        """
        params = {"recipe_id": recipe_id}

        try:
            data = await self._make_request("recipe.get.v2", params)
        except APIError as e:
            if e.error_code == 107:  # Recipe not found
                raise RecipeNotFoundError(f"Recipe with ID {recipe_id} not found", 107)
            raise

        # Parse the response
        recipe_data = data.get("recipe", {})

        # Handle ingredients
        ingredients_data = recipe_data.get("ingredients", {}).get("ingredient", [])
        if not isinstance(ingredients_data, list):
            ingredients_data = [ingredients_data]

        from .models import RecipeIngredient

        recipe_data["ingredients"] = [
            RecipeIngredient(**ing) for ing in ingredients_data
        ]

        # Handle serving sizes
        servings_data = recipe_data.get("serving_sizes", {}).get("serving", [])
        if not isinstance(servings_data, list):
            servings_data = [servings_data]

        from .models import RecipeServing

        recipe_data["serving_sizes"] = [RecipeServing(**s) for s in servings_data]

        # Handle directions
        directions_data = recipe_data.get("directions", {}).get("direction", [])
        if not isinstance(directions_data, list):
            directions_data = [directions_data]

        # Extract just the description text from each direction
        recipe_data["directions"] = [
            d.get("direction_description", "") if isinstance(d, dict) else str(d)
            for d in directions_data
        ]

        # Handle recipe types
        types_data = recipe_data.get("recipe_types", {}).get("recipe_type", [])
        if types_data:
            if not isinstance(types_data, list):
                types_data = [types_data]
            from .models import RecipeType

            recipe_data["recipe_types"] = [RecipeType(**t) for t in types_data]

        # Handle recipe categories
        categories_data = recipe_data.get("recipe_categories", {}).get(
            "recipe_category", []
        )
        if categories_data:
            if not isinstance(categories_data, list):
                categories_data = [categories_data]
            from .models import RecipeCategory

            recipe_data["recipe_categories"] = [
                RecipeCategory(**c) for c in categories_data
            ]

        return Recipe(**recipe_data)

    # ========================================================================
    # User-Authenticated Methods (require 3-legged OAuth)
    # ========================================================================

    async def get_food_diary(self, date: int | None = None) -> FoodDiary:
        """Get food diary entries for a specific date.

        Args:
            date: Date as integer (days since epoch). Defaults to today.

        Returns:
            Food diary containing entries for the specified date.

        Raises:
            UserNotAuthenticatedError: If user is not authenticated.
        """
        self._require_user_auth()

        # Default to today if no date specified
        if date is None:
            from datetime import datetime

            epoch = datetime(1970, 1, 1)
            today = datetime.now()
            date = (today - epoch).days

        params: dict[str, Any] = {"date": date}

        data = await self._make_request("food_entries.get.v2", params)

        # Parse the response
        entries_data = data.get("food_entries", {})

        # Handle case where no entries exist (API returns null)
        if not entries_data or "food_entry" not in entries_data:
            return FoodDiary(food_entries=[], date_int=date)

        # Parse food entries
        entry_list = entries_data.get("food_entry", [])
        if not isinstance(entry_list, list):
            entry_list = [entry_list]

        entries = []
        for entry in entry_list:
            # API returns nutrition info flat on the entry, build serving from it
            serving = FoodEntryServing(
                serving_id=entry.get("serving_id", ""),
                serving_description=entry.get("food_entry_description"),
                number_of_units=float(entry["number_of_units"])
                if entry.get("number_of_units")
                else None,
                calories=float(entry["calories"]) if entry.get("calories") else None,
                fat=float(entry["fat"]) if entry.get("fat") else None,
                carbohydrate=float(entry["carbohydrate"])
                if entry.get("carbohydrate")
                else None,
                protein=float(entry["protein"]) if entry.get("protein") else None,
                sodium=float(entry["sodium"]) if entry.get("sodium") else None,
                sugar=float(entry["sugar"]) if entry.get("sugar") else None,
            )

            entries.append(
                FoodEntry(
                    food_entry_id=entry["food_entry_id"],
                    food_id=entry["food_id"],
                    food_entry_name=entry["food_entry_name"],
                    meal=entry.get("meal"),
                    serving=serving,
                    date_int=int(entry["date_int"]) if entry.get("date_int") else None,
                )
            )

        return FoodDiary(food_entries=entries, date_int=date)

    async def add_food_entry(
        self,
        food_id: int,
        serving_id: int,
        number_of_units: float,
        meal: str = "other",
        date: int | None = None,
        food_entry_name: str | None = None,
    ) -> str:
        """Add a food entry to the diary.

        Args:
            food_id: The FatSecret food ID.
            serving_id: The serving ID to use.
            number_of_units: Number of servings.
            meal: Meal type ("breakfast", "lunch", "dinner", "other").
            date: Date as integer (days since epoch). Defaults to today.
            food_entry_name: Optional custom name for the entry.

        Returns:
            The food_entry_id of the created entry.

        Raises:
            UserNotAuthenticatedError: If user is not authenticated.
        """
        self._require_user_auth()

        params: dict[str, Any] = {
            "food_id": food_id,
            "serving_id": serving_id,
            "number_of_units": number_of_units,
            "meal": meal,
        }

        if date is not None:
            params["date"] = date

        if food_entry_name is not None:
            params["food_entry_name"] = food_entry_name

        data = await self._make_request("food_entry.create", params)

        return data.get("food_entry_id", {}).get("value", "")

    async def delete_food_entry(self, food_entry_id: str) -> None:
        """Delete a food entry from the diary.

        Args:
            food_entry_id: The ID of the food entry to delete.

        Raises:
            UserNotAuthenticatedError: If user is not authenticated.
        """
        self._require_user_auth()

        await self._make_request("food_entry.delete", {"food_entry_id": food_entry_id})

    async def get_weight_month(self, date: int | None = None) -> WeightResult:
        """Get weight entries for a month.

        Args:
            date: Any date in the month as integer (days since epoch).
                  Defaults to current month.

        Returns:
            Weight result containing entries for the month.

        Raises:
            UserNotAuthenticatedError: If user is not authenticated.
        """
        self._require_user_auth()

        # Default to today if no date specified
        if date is None:
            from datetime import datetime

            epoch = datetime(1970, 1, 1)
            today = datetime.now()
            date = (today - epoch).days

        params: dict[str, Any] = {"date": date}

        data = await self._make_request("weights.get_month", params)

        # Parse the response
        month_data = data.get("month", {})

        # Handle case where no entries exist
        if not month_data or "day" not in month_data:
            return WeightResult(month=[])

        # Parse weight entries
        day_list = month_data.get("day", [])
        if not isinstance(day_list, list):
            day_list = [day_list]

        entries = [WeightEntry(**day) for day in day_list]

        return WeightResult(month=entries)

    async def update_weight(
        self,
        weight_kg: float,
        date: int | None = None,
        comment: str | None = None,
    ) -> None:
        """Record or update a weight entry.

        Args:
            weight_kg: Weight in kilograms.
            date: Date as integer (days since epoch). Defaults to today.
            comment: Optional comment for the entry.

        Raises:
            UserNotAuthenticatedError: If user is not authenticated.
        """
        self._require_user_auth()

        params: dict[str, Any] = {"current_weight_kg": weight_kg}

        if date is not None:
            params["date"] = date

        if comment is not None:
            params["comment"] = comment

        await self._make_request("weight.update", params)
