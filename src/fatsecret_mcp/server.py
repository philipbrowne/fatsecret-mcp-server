"""FatSecret MCP Server implementation using FastMCP."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api_client import FatSecretClient
from .config import Settings, get_settings
from .exceptions import (
    APIError,
    BarcodeNotFoundError,
    ConfigurationError,
    FoodNotFoundError,
    OAuthFlowError,
    RateLimitError,
    RecipeNotFoundError,
    UserNotAuthenticatedError,
)
from .oauth_flow import OAuthFlowManager
from .token_store import EnvTokenStore, TokenStore

# Module-level holders for lifespan management
_client: FatSecretClient | None = None
_token_store: TokenStore | None = None
_oauth_flow: OAuthFlowManager | None = None
_settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: Any):
    """Lifespan context manager for the MCP server.

    Creates and manages the FatSecretClient lifecycle.
    """
    global _client, _token_store, _oauth_flow, _settings

    # Initialize settings and client
    try:
        _settings = get_settings()
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load settings. Ensure FATSECRET_CONSUMER_KEY and "
            f"FATSECRET_CONSUMER_SECRET environment variables are set: {e}"
        ) from e

    # Initialize token store - use env vars on cloud deployments
    # Railway sets RAILWAY_ENVIRONMENT, Render sets RENDER
    import os

    is_cloud = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER")
    if is_cloud:
        _token_store = EnvTokenStore()
        _oauth_flow = None  # OAuth flow not supported on cloud
    else:
        _token_store = TokenStore(_settings.token_storage_path)
        _oauth_flow = OAuthFlowManager(_settings, _token_store)

    # Load existing user token if available
    user_token = _token_store.load_user_token()

    # Create client with or without user authentication
    _client = FatSecretClient(_settings, user_token=user_token)

    try:
        yield
    finally:
        # Clean up on shutdown
        if _client:
            await _client.close()
            _client = None
        if _oauth_flow:
            await _oauth_flow.close()
            _oauth_flow = None
        _token_store = None
        _settings = None


# Create FastMCP server with lifespan
mcp = FastMCP("fatsecret", lifespan=lifespan)


def _get_client() -> FatSecretClient:
    """Get the FatSecretClient from module state."""
    if _client is None:
        raise RuntimeError("FatSecretClient not initialized - server not running")
    return _client


def _get_token_store() -> TokenStore:
    """Get the TokenStore from module state."""
    if _token_store is None:
        raise RuntimeError("TokenStore not initialized - server not running")
    return _token_store


def _get_oauth_flow() -> OAuthFlowManager:
    """Get the OAuthFlowManager from module state."""
    if _oauth_flow is None:
        import os

        is_cloud = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER")
        if is_cloud:
            raise RuntimeError(
                "OAuth flow not available on cloud deployment. "
                "Complete OAuth locally and set FATSECRET_USER_TOKEN and "
                "FATSECRET_USER_TOKEN_SECRET environment variables."
            )
        raise RuntimeError("OAuthFlowManager not initialized - server not running")
    return _oauth_flow


def _get_settings() -> Settings:
    """Get the Settings from module state."""
    if _settings is None:
        raise RuntimeError("Settings not initialized - server not running")
    return _settings


async def _reinitialize_client() -> None:
    """Reinitialize the client with current user token.

    Called after successful authentication to update the client with
    the new user credentials.
    """
    global _client

    settings = _get_settings()
    token_store = _get_token_store()

    # Close existing client
    if _client:
        await _client.close()

    # Load the user token and create new client
    user_token = token_store.load_user_token()
    _client = FatSecretClient(settings, user_token=user_token)


def _date_to_int(date_str: str | None) -> int | None:
    """Convert a date string (YYYY-MM-DD) to FatSecret date int (days since epoch).

    FatSecret uses days since January 1, 1970 as the date format.

    Args:
        date_str: Date string in YYYY-MM-DD format, or None for today.

    Returns:
        Date as integer (days since Jan 1, 1970).
    """
    if date_str is None:
        return None
    # Parse and convert to days since epoch
    d = date.fromisoformat(date_str)
    epoch = date(1970, 1, 1)
    return (d - epoch).days


# ============================================================================
# Food Tools
# ============================================================================


@mcp.tool()
async def search_foods(query: str, page: int = 0, max_results: int = 20) -> str:
    """Search for foods by keyword.

    Search the FatSecret food database for items matching your query.
    Returns food names, descriptions, and IDs that can be used with get_food.

    Args:
        query: Search term (e.g., "apple", "chicken breast", "whole milk")
        page: Page number for pagination, starts at 0
        max_results: Maximum results per page (1-50, default 20)

    Returns:
        Formatted list of matching foods with basic information
    """
    try:
        client = _get_client()
        result = await client.search_foods(query, page, max_results)

        if not result.foods:
            return f"No foods found matching '{query}'."

        # Format the results
        output = [
            f"Found {result.total_results} foods matching '{query}' "
            f"(showing page {result.page_number}, {len(result.foods)} results):\n"
        ]

        for i, food in enumerate(result.foods, 1):
            brand = f" - {food.brand_name}" if food.brand_name else ""
            output.append(
                f"{i}. {food.food_name}{brand}\n"
                f"   ID: {food.food_id} | Type: {food.food_type}\n"
                f"   {food.food_description}"
            )

        return "\n\n".join(output)

    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error searching foods: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_food(food_id: int) -> str:
    """Get detailed nutrition information for a specific food.

    Retrieve complete nutritional data including all available serving sizes
    and their nutrient breakdowns.

    Args:
        food_id: The FatSecret food ID (from search_foods)

    Returns:
        Detailed nutrition information with all serving sizes
    """
    try:
        client = _get_client()
        food = await client.get_food(food_id)

        # Format the output
        output = [f"Food: {food.food_name}"]

        if food.brand_name:
            output.append(f"Brand: {food.brand_name}")

        output.append(f"Type: {food.food_type}")

        if food.food_url:
            output.append(f"URL: {food.food_url}")

        output.append(f"\nAvailable Servings ({len(food.servings)}):")

        for i, serving in enumerate(food.servings, 1):
            output.append(f"\n{i}. {serving.serving_description}")

            # Show metric info if available
            if serving.metric_serving_amount and serving.metric_serving_unit:
                output.append(
                    f"   Metric: {serving.metric_serving_amount} "
                    f"{serving.metric_serving_unit}"
                )

            # Show key nutrients
            nutrients = []
            if serving.calories is not None:
                nutrients.append(f"Calories: {serving.calories}")
            if serving.protein is not None:
                nutrients.append(f"Protein: {serving.protein}g")
            if serving.carbohydrate is not None:
                nutrients.append(f"Carbs: {serving.carbohydrate}g")
            if serving.fat is not None:
                nutrients.append(f"Fat: {serving.fat}g")

            if nutrients:
                output.append(f"   {' | '.join(nutrients)}")

            # Show detailed nutrients
            details = []
            if serving.saturated_fat is not None:
                details.append(f"Saturated Fat: {serving.saturated_fat}g")
            if serving.trans_fat is not None:
                details.append(f"Trans Fat: {serving.trans_fat}g")
            if serving.cholesterol is not None:
                details.append(f"Cholesterol: {serving.cholesterol}mg")
            if serving.sodium is not None:
                details.append(f"Sodium: {serving.sodium}mg")
            if serving.fiber is not None:
                details.append(f"Fiber: {serving.fiber}g")
            if serving.sugar is not None:
                details.append(f"Sugar: {serving.sugar}g")

            if details:
                output.append(f"   {', '.join(details)}")

        return "\n".join(output)

    except FoodNotFoundError:
        return f"Error: Food with ID {food_id} not found."
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error retrieving food: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def lookup_barcode(barcode: str) -> str:
    """Find food by product barcode.

    Look up a food item using its UPC or EAN barcode. Returns the same
    detailed information as get_food.

    Args:
        barcode: Product barcode (UPC/EAN, e.g., "041220576920")

    Returns:
        Detailed nutrition information for the scanned product
    """
    try:
        client = _get_client()
        food = await client.find_food_by_barcode(barcode)

        # Reuse the get_food formatting
        output = [f"Barcode: {barcode}\n"]
        output.append(f"Food: {food.food_name}")

        if food.brand_name:
            output.append(f"Brand: {food.brand_name}")

        output.append(f"Type: {food.food_type}")
        output.append(f"\nAvailable Servings ({len(food.servings)}):")

        for i, serving in enumerate(food.servings, 1):
            output.append(f"\n{i}. {serving.serving_description}")

            # Show key nutrients
            nutrients = []
            if serving.calories is not None:
                nutrients.append(f"Calories: {serving.calories}")
            if serving.protein is not None:
                nutrients.append(f"Protein: {serving.protein}g")
            if serving.carbohydrate is not None:
                nutrients.append(f"Carbs: {serving.carbohydrate}g")
            if serving.fat is not None:
                nutrients.append(f"Fat: {serving.fat}g")

            if nutrients:
                output.append(f"   {' | '.join(nutrients)}")

        return "\n".join(output)

    except BarcodeNotFoundError:
        return f"Error: Barcode '{barcode}' not found in database."
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error looking up barcode: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# Recipe Tools
# ============================================================================


@mcp.tool()
async def search_recipes(query: str, page: int = 0, max_results: int = 20) -> str:
    """Search for recipes by keyword.

    Search the FatSecret recipe database for recipes matching your query.
    Returns recipe names, descriptions, and IDs that can be used with get_recipe.

    Args:
        query: Search term (e.g., "chocolate cake", "chicken soup", "pasta")
        page: Page number for pagination, starts at 0
        max_results: Maximum results per page (1-50, default 20)

    Returns:
        Formatted list of matching recipes with basic information
    """
    try:
        client = _get_client()
        result = await client.search_recipes(query, page, max_results)

        if not result.recipes:
            return f"No recipes found matching '{query}'."

        # Format the results
        output = [
            f"Found {result.total_results} recipes matching '{query}' "
            f"(showing page {result.page_number}, {len(result.recipes)} results):\n"
        ]

        for i, recipe in enumerate(result.recipes, 1):
            output.append(f"{i}. {recipe.recipe_name}")
            output.append(f"   ID: {recipe.recipe_id}")

            # Show timing and servings
            info = []
            if recipe.preparation_time_min:
                info.append(f"Prep: {recipe.preparation_time_min} min")
            if recipe.cooking_time_min:
                info.append(f"Cook: {recipe.cooking_time_min} min")
            if recipe.number_of_servings:
                info.append(f"Servings: {recipe.number_of_servings}")
            if recipe.rating:
                info.append(f"Rating: {recipe.rating:.1f}/5")

            if info:
                output.append(f"   {' | '.join(info)}")

            # Show description
            if recipe.recipe_description:
                desc = recipe.recipe_description
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                output.append(f"   {desc}")

            output.append("")

        return "\n".join(output)

    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error searching recipes: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_recipe(recipe_id: int) -> str:
    """Get full recipe with ingredients, directions, and nutrition.

    Retrieve complete recipe details including ingredient list, step-by-step
    directions, and nutritional information per serving.

    Args:
        recipe_id: The FatSecret recipe ID (from search_recipes)

    Returns:
        Complete recipe with ingredients, directions, and nutrition
    """
    try:
        client = _get_client()
        recipe = await client.get_recipe(recipe_id)

        # Format the output
        output = [f"Recipe: {recipe.recipe_name}\n"]

        # Show description
        if recipe.recipe_description:
            output.append(f"{recipe.recipe_description}\n")

        # Show metadata
        info = []
        if recipe.preparation_time_min:
            info.append(f"Prep: {recipe.preparation_time_min} min")
        if recipe.cooking_time_min:
            info.append(f"Cook: {recipe.cooking_time_min} min")
        if recipe.number_of_servings:
            info.append(f"Servings: {recipe.number_of_servings}")
        if recipe.rating and recipe.number_of_ratings:
            info.append(
                f"Rating: {recipe.rating:.1f}/5 ({recipe.number_of_ratings} ratings)"
            )

        if info:
            output.append(" | ".join(info))
            output.append("")

        # Show categories/types
        if recipe.recipe_types:
            types = [t.recipe_type for t in recipe.recipe_types]
            output.append(f"Types: {', '.join(types)}")

        if recipe.recipe_categories:
            categories = [c.recipe_category for c in recipe.recipe_categories]
            output.append(f"Categories: {', '.join(categories)}")

        if recipe.recipe_types or recipe.recipe_categories:
            output.append("")

        # Show ingredients
        output.append(f"Ingredients ({len(recipe.ingredients)}):")
        for i, ingredient in enumerate(recipe.ingredients, 1):
            output.append(f"{i}. {ingredient.ingredient_description}")

        output.append("")

        # Show directions
        if recipe.directions:
            output.append(f"Directions ({len(recipe.directions)} steps):")
            for i, direction in enumerate(recipe.directions, 1):
                output.append(f"{i}. {direction}")

            output.append("")

        # Show nutrition
        if recipe.serving_sizes:
            output.append("Nutrition Information:")
            for i, serving in enumerate(recipe.serving_sizes, 1):
                if len(recipe.serving_sizes) > 1:
                    size_info = serving.serving_size or f"Serving {i}"
                    output.append(f"\n{size_info}:")
                else:
                    output.append("")

                nutrients = []
                if serving.calories is not None:
                    nutrients.append(f"Calories: {serving.calories}")
                if serving.protein is not None:
                    nutrients.append(f"Protein: {serving.protein}g")
                if serving.carbohydrate is not None:
                    nutrients.append(f"Carbs: {serving.carbohydrate}g")
                if serving.fat is not None:
                    nutrients.append(f"Fat: {serving.fat}g")

                if nutrients:
                    output.append(" | ".join(nutrients))

                # Show detailed nutrients
                details = []
                if serving.saturated_fat is not None:
                    details.append(f"Saturated Fat: {serving.saturated_fat}g")
                if serving.cholesterol is not None:
                    details.append(f"Cholesterol: {serving.cholesterol}mg")
                if serving.sodium is not None:
                    details.append(f"Sodium: {serving.sodium}mg")
                if serving.fiber is not None:
                    details.append(f"Fiber: {serving.fiber}g")
                if serving.sugar is not None:
                    details.append(f"Sugar: {serving.sugar}g")

                if details:
                    output.append(", ".join(details))

        # Show URL if available
        if recipe.recipe_url:
            output.append(f"\nView online: {recipe.recipe_url}")

        return "\n".join(output)

    except RecipeNotFoundError:
        return f"Error: Recipe with ID {recipe_id} not found."
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error retrieving recipe: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# Authentication Tools
# ============================================================================


@mcp.tool()
async def check_auth_status() -> str:
    """Check if a FatSecret user account is connected.

    Returns whether you have user authentication configured, which is
    required for food diary, weight tracking, and other personal features.

    Returns:
        Authentication status message
    """
    try:
        client = _get_client()

        if client.is_user_authenticated:
            return (
                "Connected: Your FatSecret account is linked.\n"
                "You can use food diary, weight tracking, and other personal features."
            )
        else:
            return (
                "Not connected: No FatSecret account is linked.\n"
                "Use start_authentication to connect your account and enable "
                "food diary, weight tracking, and other personal features."
            )
    except Exception as e:
        return f"Error checking auth status: {str(e)}"


@mcp.tool()
async def start_authentication() -> str:
    """Start the FatSecret account connection process.

    Begins the OAuth authentication flow. Returns a URL that the user must
    visit to authorize the connection. After authorizing, the user will
    receive a verification code to use with complete_authentication.

    Note: Not available on cloud deployments. Complete OAuth locally first.

    Returns:
        Instructions with the authorization URL
    """
    try:
        oauth_flow = _get_oauth_flow()

        # Get request token
        request_token = await oauth_flow.get_request_token()

        # Generate authorization URL
        auth_url = oauth_flow.get_authorization_url(request_token)

        return (
            "To connect your FatSecret account:\n\n"
            f"1. Visit this URL:\n   {auth_url}\n\n"
            "2. Log in to FatSecret and authorize the connection\n\n"
            "3. Copy the verification code shown\n\n"
            "4. Use complete_authentication with the code to finish setup"
        )

    except RuntimeError as e:
        return str(e)
    except OAuthFlowError as e:
        return f"Error starting authentication: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def complete_authentication(verifier: str) -> str:
    """Complete the FatSecret account connection.

    Finish the OAuth authentication flow using the verification code
    obtained from the authorization page.

    Args:
        verifier: The verification code from FatSecret's authorization page

    Returns:
        Success or error message
    """
    try:
        oauth_flow = _get_oauth_flow()

        # Exchange verifier for access token
        await oauth_flow.exchange_for_access_token(verifier)

        # Reinitialize client with new credentials
        await _reinitialize_client()

        return (
            "Success! Your FatSecret account is now connected.\n"
            "You can now use food diary, weight tracking, and other personal features."
        )

    except OAuthFlowError as e:
        return f"Error completing authentication: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def disconnect_account() -> str:
    """Disconnect your FatSecret account.

    Remove stored credentials and disconnect from your FatSecret account.
    You will need to re-authenticate to use personal features again.

    Returns:
        Confirmation message
    """
    try:
        token_store = _get_token_store()

        # Delete stored tokens
        token_store.delete_user_token()
        token_store.clear_request_token()

        # Reinitialize client without user auth
        await _reinitialize_client()

        return (
            "Disconnected: Your FatSecret account has been unlinked.\n"
            "Food diary and weight tracking features are no longer available.\n"
            "Use start_authentication to connect again."
        )

    except Exception as e:
        return f"Error disconnecting account: {str(e)}"


# ============================================================================
# Food Diary Tools
# ============================================================================


@mcp.tool()
async def get_food_diary(date: str | None = None) -> str:
    """Get food diary entries for a specific date.

    Retrieve all food entries logged for a given date. Requires a connected
    FatSecret account.

    Args:
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        List of food diary entries with nutritional information
    """
    try:
        client = _get_client()
        date_int = _date_to_int(date)

        diary = await client.get_food_diary(date_int)

        if not diary.food_entries:
            date_str = date or "today"
            return f"No food entries found for {date_str}."

        # Format the results
        output = [f"Food diary for {date or 'today'}:\n"]

        # Group by meal
        meals: dict[str, list] = {
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "other": [],
        }
        for entry in diary.food_entries:
            meal = entry.meal or "other"
            meals.get(meal, meals["other"]).append(entry)

        for meal_name, entries in meals.items():
            if entries:
                output.append(f"\n{meal_name.capitalize()}:")
                for entry in entries:
                    output.append(f"  - {entry.food_entry_name}")
                    if entry.serving:
                        s = entry.serving
                        info = []
                        if s.calories is not None:
                            info.append(f"{s.calories} cal")
                        if s.protein is not None:
                            info.append(f"{s.protein}g protein")
                        if s.carbohydrate is not None:
                            info.append(f"{s.carbohydrate}g carbs")
                        if s.fat is not None:
                            info.append(f"{s.fat}g fat")
                        if info:
                            output.append(f"    {' | '.join(info)}")

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to FatSecret.\n"
            "Use start_authentication to connect your account first."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting food diary: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def add_food_to_diary(
    food_id: int,
    serving_id: int,
    amount: float,
    meal: str = "other",
    date: str | None = None,
) -> str:
    """Add a food entry to your diary.

    Log a food item to your food diary. Use search_foods and get_food to find
    the food_id and serving_id. Requires a connected FatSecret account.

    Args:
        food_id: The FatSecret food ID (from search_foods or get_food)
        serving_id: The serving ID (from get_food serving details)
        amount: Number of servings (e.g., 1.5 for 1.5 servings)
        meal: Meal type - "breakfast", "lunch", "dinner", or "other"
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        Confirmation with the entry ID
    """
    try:
        client = _get_client()
        date_int = _date_to_int(date)

        entry_id = await client.add_food_entry(
            food_id=food_id,
            serving_id=serving_id,
            number_of_units=amount,
            meal=meal,
            date=date_int,
        )

        return f"Added to {meal}: Food entry created (ID: {entry_id})"

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to FatSecret.\n"
            "Use start_authentication to connect your account first."
        )
    except FoodNotFoundError:
        return f"Error: Food with ID {food_id} not found."
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error adding food entry: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def delete_food_from_diary(food_entry_id: str) -> str:
    """Delete a food entry from your diary.

    Remove a previously logged food entry. Use get_food_diary to find entry IDs.
    Requires a connected FatSecret account.

    Args:
        food_entry_id: The food entry ID to delete (from get_food_diary)

    Returns:
        Confirmation message
    """
    try:
        client = _get_client()

        await client.delete_food_entry(food_entry_id)

        return f"Deleted food entry {food_entry_id}"

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to FatSecret.\n"
            "Use start_authentication to connect your account first."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error deleting food entry: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# Weight Tracking Tools
# ============================================================================


@mcp.tool()
async def get_weight_history(month: str | None = None) -> str:
    """Get weight entries for a month.

    Retrieve all weight entries logged during a specific month.
    Requires a connected FatSecret account.

    Args:
        month: Any date in the month (YYYY-MM-DD format), defaults to current month

    Returns:
        List of weight entries for the month
    """
    try:
        client = _get_client()
        date_int = _date_to_int(month)

        result = await client.get_weight_month(date_int)

        if not result.month:
            month_str = month[:7] if month else "this month"
            return f"No weight entries found for {month_str}."

        # Format the results
        output = ["Weight history:\n"]

        for entry in result.month:
            # Convert date_int (days since epoch) to readable format
            from datetime import timedelta

            epoch = date(1970, 1, 1)
            entry_date = epoch + timedelta(days=entry.date_int)
            formatted_date = entry_date.strftime("%Y-%m-%d")

            weight_str = ""
            if entry.weight_kg is not None:
                weight_str = f"{entry.weight_kg} kg"
                if entry.weight_lb is not None:
                    weight_str += f" ({entry.weight_lb} lb)"
            elif entry.weight_lb is not None:
                weight_str = f"{entry.weight_lb} lb"

            line = f"  {formatted_date}: {weight_str}"
            if entry.comment:
                line += f" - {entry.comment}"

            output.append(line)

        return "\n".join(output)

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to FatSecret.\n"
            "Use start_authentication to connect your account first."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error getting weight history: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def log_weight(
    weight: float,
    unit: str = "kg",
    date: str | None = None,
    comment: str | None = None,
) -> str:
    """Log your weight.

    Record a weight entry for tracking progress. Requires a connected
    FatSecret account.

    Args:
        weight: Weight value
        unit: Unit of measurement - "kg" or "lb"
        date: Date in YYYY-MM-DD format (defaults to today)
        comment: Optional note for this entry

    Returns:
        Confirmation message
    """
    try:
        client = _get_client()
        date_int = _date_to_int(date)

        # Convert to kg if needed
        weight_kg = weight
        if unit.lower() == "lb":
            weight_kg = weight * 0.453592

        await client.update_weight(
            weight_kg=weight_kg,
            date=date_int,
            comment=comment,
        )

        date_str = date or "today"
        return f"Logged weight: {weight} {unit} for {date_str}"

    except UserNotAuthenticatedError:
        return (
            "Error: Not connected to FatSecret.\n"
            "Use start_authentication to connect your account first."
        )
    except RateLimitError:
        return "Error: API rate limit exceeded. Please try again later."
    except APIError as e:
        return f"Error logging weight: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Run the FatSecret MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
