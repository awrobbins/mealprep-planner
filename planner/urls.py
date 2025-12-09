from django.urls import path
from . import views

app_name = "planner"

urlpatterns = [
   #Recipes
   path("", views.home, name="home"),
   path("recipes/", views.recipe_list, name="recipe_list"),
   path("recipes/new/", views.recipe_create, name="recipe_create"),
   path("recipes/<int:pk>/", views.recipe_detail, name="recipe_detail"),
   path("recipes/<int:pk>/edit/", views.recipe_edit, name="recipe_edit"),
   path("recipes/<int:pk>/pdf/", views.recipe_pdf, name="recipe_pdf"),

   # Meal plan weeks
   path("mealplans/", views.mealplan_week_list, name="mealplan_week_list"),
   path("mealplans/new/", views.mealplan_week_create, name="mealplan_week_create"),
   path("mealplans/<int:pk>/", views.mealplan_week_detail, name="mealplan_week_detail"),
   path("mealplans/<int:pk>/autobuild/", views.mealplan_week_autobuild, name="mealplan_week_autobuild"),
   path("mealplans/<int:pk>/archive/", views.mealplan_week_archive, name="mealplan_week_archive"),
   path("mealplans/<int:pk>/unarchive/", views.mealplan_week_unarchive, name="mealplan_week_unarchive"),
   path("mealplans/<int:pk>/delete/", views.mealplan_week_delete, name="mealplan_week_delete"),

      # Toggle skip on individual meals
   path(
       "meals/<int:pk>/toggle-skip/",
       views.planned_meal_toggle_skip,
       name="planned_meal_toggle_skip",
   ),

   # Manual planned meal management
   path(
       "mealplans/<int:week_pk>/meals/add/",
       views.planned_meal_create,
       name="planned_meal_create",
   ),
   path(
       "meals/<int:pk>/edit/",
       views.planned_meal_edit,
       name="planned_meal_edit",
   ),
   path(
       "meals/<int:pk>/delete/",
       views.planned_meal_delete,
       name="planned_meal_delete",
   ),

   # Shopping List
   path("shopping-list/", views.shopping_list, name="shopping_list"),
   path("shopping-list/pdf/", views.shopping_list_pdf, name="shopping_list_pdf"),
]


