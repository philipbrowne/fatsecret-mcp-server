"""
Pydantic models for FatSecret API responses.
"""

from pydantic import BaseModel, Field

# ============================================================================
# Food Models
# ============================================================================


class FoodServing(BaseModel):
    """Model for a food serving."""

    serving_id: str
    serving_description: str
    metric_serving_amount: float | None = None
    metric_serving_unit: str | None = None
    number_of_units: float | None = None
    measurement_description: str | None = None
    calories: float | None = None
    fat: float | None = None
    saturated_fat: float | None = None
    polyunsaturated_fat: float | None = None
    monounsaturated_fat: float | None = None
    trans_fat: float | None = None
    cholesterol: float | None = None
    sodium: float | None = None
    potassium: float | None = None
    carbohydrate: float | None = None
    fiber: float | None = None
    sugar: float | None = None
    protein: float | None = None
    vitamin_a: float | None = None
    vitamin_c: float | None = None
    calcium: float | None = None
    iron: float | None = None
    added_sugars: float | None = None
    vitamin_d: float | None = None


class Food(BaseModel):
    """Model for detailed food information."""

    food_id: str
    food_name: str
    food_type: str
    brand_name: str | None = None
    food_url: str | None = None
    food_description: str | None = None
    servings: list[FoodServing] = Field(default_factory=list)


class FoodSearchItem(BaseModel):
    """Model for a food item in search results."""

    food_id: str
    food_name: str
    food_type: str
    brand_name: str | None = None
    food_description: str


class FoodSearchResult(BaseModel):
    """Model for food search results."""

    foods: list[FoodSearchItem] = Field(default_factory=list)
    max_results: int
    total_results: int
    page_number: int


# ============================================================================
# Recipe Models
# ============================================================================


class RecipeIngredient(BaseModel):
    """Model for a recipe ingredient."""

    food_id: str | None = None
    food_name: str
    ingredient_description: str
    ingredient_url: str | None = None
    number_of_units: float | None = None
    measurement_description: str | None = None
    serving_id: str | None = None


class RecipeServing(BaseModel):
    """Model for recipe serving information."""

    serving_size: str | None = None
    calories: float | None = None
    fat: float | None = None
    saturated_fat: float | None = None
    polyunsaturated_fat: float | None = None
    monounsaturated_fat: float | None = None
    trans_fat: float | None = None
    cholesterol: float | None = None
    sodium: float | None = None
    potassium: float | None = None
    carbohydrate: float | None = None
    fiber: float | None = None
    sugar: float | None = None
    protein: float | None = None
    vitamin_a: float | None = None
    vitamin_c: float | None = None
    calcium: float | None = None
    iron: float | None = None


class RecipeType(BaseModel):
    """Model for recipe type information."""

    recipe_type: str
    recipe_type_description: str | None = None


class RecipeCategory(BaseModel):
    """Model for recipe category information."""

    recipe_category: str
    recipe_category_description: str | None = None


class Recipe(BaseModel):
    """Model for detailed recipe information."""

    recipe_id: str
    recipe_name: str
    recipe_description: str
    recipe_url: str | None = None
    recipe_image: str | None = None
    recipe_images: dict[str, str] | None = None
    preparation_time_min: int | None = None
    cooking_time_min: int | None = None
    number_of_servings: int | None = None
    rating: float | None = None
    number_of_ratings: int | None = None
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    serving_sizes: list[RecipeServing] = Field(default_factory=list)
    directions: list[str] = Field(default_factory=list)
    recipe_types: list[RecipeType] | None = None
    recipe_categories: list[RecipeCategory] | None = None


class RecipeSearchItem(BaseModel):
    """Model for a recipe item in search results."""

    recipe_id: str
    recipe_name: str
    recipe_description: str
    recipe_url: str | None = None
    recipe_image: str | None = None
    recipe_images: dict[str, str] | None = None
    preparation_time_min: int | None = None
    cooking_time_min: int | None = None
    number_of_servings: int | None = None
    rating: float | None = None


class RecipeSearchResult(BaseModel):
    """Model for recipe search results."""

    recipes: list[RecipeSearchItem] = Field(default_factory=list)
    max_results: int
    total_results: int
    page_number: int


# ============================================================================
# NLP Models
# ============================================================================


class NLPFood(BaseModel):
    """Model for a food item from NLP parsing."""

    food_id: str
    food_entry_name: str
    serving_id: str | None = None
    number_of_units: float | None = None
    measurement_description: str | None = None
    eaten_calories: float | None = Field(None, alias="calories")
    eaten_fat: float | None = Field(None, alias="fat")
    eaten_saturated_fat: float | None = Field(None, alias="saturated_fat")
    eaten_carbohydrate: float | None = Field(None, alias="carbohydrate")
    eaten_fiber: float | None = Field(None, alias="fiber")
    eaten_sugar: float | None = Field(None, alias="sugar")
    eaten_protein: float | None = Field(None, alias="protein")
    eaten_sodium: float | None = Field(None, alias="sodium")
    eaten_cholesterol: float | None = Field(None, alias="cholesterol")
    eaten_potassium: float | None = Field(None, alias="potassium")

    model_config = {"populate_by_name": True}


class NLPResult(BaseModel):
    """Model for NLP parsing results."""

    foods: list[NLPFood] = Field(default_factory=list)


# ============================================================================
# Weight Tracking Models
# ============================================================================


class WeightEntry(BaseModel):
    """Model for a weight entry."""

    date_int: int
    weight_kg: float | None = None
    weight_lb: float | None = None
    comment: str | None = None
    weight_type: str | None = None


class WeightResult(BaseModel):
    """Model for weight tracking results."""

    month: list[WeightEntry] = Field(default_factory=list)


# ============================================================================
# Exercise Models
# ============================================================================


class Exercise(BaseModel):
    """Model for exercise information."""

    exercise_id: str
    exercise_name: str
    exercise_description: str | None = None


class ExerciseEntry(BaseModel):
    """Model for an exercise entry."""

    exercise_entry_id: str
    exercise_id: str
    exercise_name: str
    duration_min: int | None = None
    calories: float | None = None
    date_int: int | None = None
    is_cardio: bool | None = None


# ============================================================================
# Food Diary Models
# ============================================================================


class FoodEntryServing(BaseModel):
    """Model for a food diary entry serving."""

    serving_id: str
    serving_description: str | None = None
    number_of_units: float | None = None
    measurement_description: str | None = None
    calories: float | None = None
    fat: float | None = None
    carbohydrate: float | None = None
    protein: float | None = None
    sodium: float | None = None
    sugar: float | None = None


class FoodEntry(BaseModel):
    """Model for a food diary entry."""

    food_entry_id: str
    food_id: str
    food_entry_name: str
    meal: str | None = None
    serving: FoodEntryServing | None = None
    date_int: int | None = None


class FoodDiary(BaseModel):
    """Model for food diary results."""

    food_entries: list[FoodEntry] = Field(default_factory=list)
    date_int: int | None = None


# ============================================================================
# Authentication Models
# ============================================================================


class AuthToken(BaseModel):
    """Model for authentication token."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None


class RequestToken(BaseModel):
    """Model for OAuth1 request token (temporary during OAuth flow)."""

    oauth_token: str
    oauth_token_secret: str


class UserToken(BaseModel):
    """Model for OAuth1 user access token (persistent after authentication)."""

    oauth_token: str
    oauth_token_secret: str
    created_at: float | None = None
