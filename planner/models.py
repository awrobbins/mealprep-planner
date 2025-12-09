from django.db import models
from django.utils import timezone
 
# Create your models here.

#Categories for shopping list group
INGREDIENT_CATEGORIES = [
	("pantry", "Pantry"),
	("produce", "Produce"),
	("protein", "Protein"),
	("frozen", "Frozen"),
	("dairy", "Dairy"),
]

#Meal types to support the weekly plan generator
MEAL_TYPES = [
	("lunch", "Lunch"),
	("vegetarian", "Vegetarian Dinner"),
	("seafood", "Seafood Dinner"),
	("protein", "Protein Dinner"),
	("other", "Other")
]

class Recipe(models.Model):
	name = models.CharField(max_length=200)
	course_count = models.PositiveIntegerField()
	meal_type = models.CharField(max_length=20, choices=MEAL_TYPES, default="other")
	source_note = models.CharField(
        max_length=200,
        blank=True,
        help_text="Skinnytaste book + page, or 'Online'.",
    )
	last_used = models.DateField(null=True, blank=True)

	def __str__(self):
		return self.name

class Ingredient(models.Model):
	recipe = models.ForeignKey(Recipe, related_name="ingredients", on_delete=models.CASCADE)
	name = models.CharField(max_length=200)
	amount = models.CharField(max_length=100, blank=True) #"1 can", "15.5oz", etc. 
	category = models.CharField(max_length=20, choices=INGREDIENT_CATEGORIES)

	def __str__(self):
		return f"{self.name} ({self.recipe.name})"

class MealPlanWeek(models.Model):
	label = models.CharField(max_length=50) #"Week 1" "Week 2", etc
	start_date = models.DateField(null=True, blank=True)
	skipped = models.BooleanField(default=False)
	archived = models.BooleanField(default=False)

	def __str__(self):
		return self.label

class PlannedMeal(models.Model):
    week = models.ForeignKey(MealPlanWeek, related_name="meals", on_delete=models.CASCADE)
    slot_name = models.CharField(max_length=100)  # "Lunch", "Monday Dinner", etc.
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    skipped = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.slot_name}: {self.recipe.name}"


