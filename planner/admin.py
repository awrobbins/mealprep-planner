from django.contrib import admin
from .models import Recipe, Ingredient, MealPlanWeek, PlannedMeal

# Register your models here.

class IngredientInline(admin.TabularInline):
	model = Ingredient
	extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
	list_display = ("name", "course_count", "meal_type", "last_used")
	inlines = [IngredientInline]

@admin.register(MealPlanWeek)
class MealPlanWeekAdmin(admin.ModelAdmin):
	list_display = ("label", "start_date", "skipped")

@admin.register(PlannedMeal)
class PlannedMealAdmin(admin.ModelAdmin):
	list_display = ("week", "slot_name", "recipe")
