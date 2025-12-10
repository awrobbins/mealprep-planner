from django.conf import settings
from django.forms import modelform_factory, inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from .models import Recipe, Ingredient, MealPlanWeek, PlannedMeal, INGREDIENT_CATEGORIES
from datetime import date, timedelta
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .utils import render_to_pdf


# ---------- Forms ----------

RecipeForm = modelform_factory(
    Recipe,
    fields=["name", "course_count", "meal_type", "source_note"],
)

IngredientFormSet = inlineformset_factory(
    Recipe,
    Ingredient,
    fields=["name", "amount", "category"],
    extra=25,            # show 3 empty ingredient rows by default
    can_delete=True,    # allow removing rows
)

MealPlanWeekForm = modelform_factory(
    MealPlanWeek,
    fields=["label", "start_date", "skipped"],
)

PlannedMealForm = modelform_factory(
    PlannedMeal,
    fields=["slot_name", "recipe"],
)



# ---------- Views ----------

def home(request):
    greeting = getattr(settings, "MEALPREP_GREETING", "Hello, wife!")
    return render(request, "planner/home.html", {"greeting": greeting})

def recipe_create(request):
    if request.method == "POST":
        form = RecipeForm(request.POST)
        formset = IngredientFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            name = form.cleaned_data["name"]

            # Duplicate name check (case-insensitive)
            if Recipe.objects.filter(name__iexact=name).exists():
                form.add_error(
                    "name",
                    "A recipe with this name already exists. "
                    "Please choose a different name or edit the existing recipe instead."
                )
            else:
                recipe = form.save()
                formset.instance = recipe
                formset.save()
                return redirect("planner:recipe_detail", pk=recipe.pk)
    else:
        form = RecipeForm()
        formset = IngredientFormSet()

    context = {
        "form": form,
        "formset": formset,
        "title": "Build a Recipe",
        "is_edit": False,
    }
    return render(request, "planner/recipe_form.html", context)



def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, "planner/recipe_detail.html", {"recipe": recipe})

def recipe_edit(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)
        formset = IngredientFormSet(request.POST, instance=recipe)

        if form.is_valid() and formset.is_valid():
            recipe = form.save()
            formset.instance = recipe
            formset.save()
            return redirect("planner:recipe_detail", pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        formset = IngredientFormSet(instance=recipe)

    context = {
        "form": form,
        "formset": formset,
        "title": f"Edit Recipe: {recipe.name}",
        "is_edit": True,
        "recipe": recipe,
    }
    return render(request, "planner/recipe_form.html", context)


def recipe_list(request):
    recipes = Recipe.objects.all().order_by("name")
    return render(request, "planner/recipe_list.html", {"recipes": recipes})

#def mealplan_week_list(request):
#    weeks = MealPlanWeek.objects.order_by("-start_date", "-id")
#    return render(request, "planner/mealplan_week_list.html", {"weeks": weeks})

def mealplan_week_list(request):
    active_weeks = MealPlanWeek.objects.filter(archived=False).order_by("-start_date", "-id")
    archived_weeks = MealPlanWeek.objects.filter(archived=True).order_by("-start_date", "-id")
    return render(
        request,
        "planner/mealplan_week_list.html",
        {
            "weeks": active_weeks,
            "archived_weeks": archived_weeks,
        },
    )


def mealplan_week_create(request):
    if request.method == "POST":
        form = MealPlanWeekForm(request.POST)
        if form.is_valid():
            week = form.save()
            return redirect("planner:mealplan_week_detail", pk=week.pk)
    else:
        form = MealPlanWeekForm()

    return render(request, "planner/mealplan_week_form.html", {"form": form})

def mealplan_week_detail(request, pk):
    week = get_object_or_404(MealPlanWeek, pk=pk)
    meals = week.meals.select_related("recipe").all().order_by("slot_name")
    return render(
        request,
        "planner/mealplan_week_detail.html",
        {"week": week, "meals": meals, "recipes": Recipe.objects.order_by("name")},
    )

def mealplan_week_autobuild(request, pk):
    week = get_object_or_404(MealPlanWeek, pk=pk)

    if request.method != "POST":
        return redirect("planner:mealplan_week_detail", pk=week.pk)

    # If the week is marked as skipped, just go back without doing anything.
    if week.skipped:
        return redirect("planner:mealplan_week_detail", pk=week.pk)

    # Clear any existing planned meals for a clean rebuild.
    week.meals.all().delete()

    # Determine the reference date for "last used"
    reference_date = week.start_date or date.today()
    cutoff = reference_date - timedelta(days=30)

    chosen_ids = set()

    def pick_recipe(meal_type, course_count):
        qs = Recipe.objects.filter(
            meal_type=meal_type,
            course_count=course_count,
        ).exclude(
            last_used__gte=cutoff
        ).exclude(
            id__in=chosen_ids
        ).order_by("last_used", "name")

        recipe = qs.first()
        if recipe is None:
            # Fallback: ignore last_used / duplicates if needed
            qs = Recipe.objects.filter(
                meal_type=meal_type,
                course_count=course_count,
            ).exclude(
                id__in=chosen_ids
            ).order_by("name")
            recipe = qs.first()

        if recipe is not None:
            chosen_ids.add(recipe.id)
        return recipe

    # Define the slots we want
    slots = [
        ("Lunch", "lunch", 8),
        ("Vegetarian Dinner", "vegetarian", 4),
        ("Protein Dinner", "protein", 4),
        ("Seafood Dinner", "seafood", 2),
    ]

    created_meals = []

    for slot_name, meal_type, course_count in slots:
        recipe = pick_recipe(meal_type, course_count)
        if recipe is not None:
            PlannedMeal.objects.create(
                week=week,
                slot_name=slot_name,
                recipe=recipe,
            )
            # Update last_used
            recipe.last_used = reference_date
            recipe.save(update_fields=["last_used"])
            created_meals.append(recipe)

    return redirect("planner:mealplan_week_detail", pk=week.pk)

@require_POST
def mealplan_week_archive(request, pk):
    week = get_object_or_404(MealPlanWeek, pk=pk)
    week.archived = True
    week.save(update_fields=["archived"])
    return redirect("planner:mealplan_week_list")


@require_POST
def mealplan_week_unarchive(request, pk):
    week = get_object_or_404(MealPlanWeek, pk=pk)
    week.archived = False
    week.save(update_fields=["archived"])
    return redirect("planner:mealplan_week_list")


@require_POST
def mealplan_week_delete(request, pk):
    week = get_object_or_404(MealPlanWeek, pk=pk)
    week.delete()
    return redirect("planner:mealplan_week_list")

@require_POST
def planned_meal_toggle_skip(request, pk):
    meal = get_object_or_404(PlannedMeal, pk=pk)
    meal.skipped = not meal.skipped
    meal.save(update_fields=["skipped"])
    return redirect("planner:mealplan_week_detail", pk=meal.week.pk)

def planned_meal_create(request, week_pk):
    """
    Manually attach any recipe (including 'Other') to a specific week.
    """
    week = get_object_or_404(MealPlanWeek, pk=week_pk)

    if request.method == "POST":
        form = PlannedMealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.week = week
            meal.save()
            return redirect("planner:mealplan_week_detail", pk=week.pk)
    else:
        # Optional: allow pre-filling slot_name via ?slot_name= query param
        initial_slot = request.GET.get("slot_name", "")
        form = PlannedMealForm(initial={"slot_name": initial_slot})

    context = {
        "form": form,
        "week": week,
        "title": "Add meal to week",
    }
    return render(request, "planner/planned_meal_form.html", context)


def planned_meal_edit(request, pk):
    """
    Change the recipe (or slot name) for an existing planned meal.
    """
    meal = get_object_or_404(PlannedMeal, pk=pk)
    if request.method == "POST":
        form = PlannedMealForm(request.POST, instance=meal)
        if form.is_valid():
            form.save()
            return redirect("planner:mealplan_week_detail", pk=meal.week.pk)
    else:
        form = PlannedMealForm(instance=meal)

    context = {
        "form": form,
        "week": meal.week,
        "meal": meal,
        "title": "Edit planned meal",
    }
    return render(request, "planner/planned_meal_form.html", context)


@require_POST
def planned_meal_delete(request, pk):
    """
    Remove a planned meal from its week entirely.
    """
    meal = get_object_or_404(PlannedMeal, pk=pk)
    week_pk = meal.week.pk
    meal.delete()
    return redirect("planner:mealplan_week_detail", pk=week_pk)


def shopping_list(request):
   #weeks = MealPlanWeek.objects.order_by("start_date", "id")
    weeks = MealPlanWeek.objects.filter(archived=False).order_by("start_date", "id")
    selected_week_ids = []
    ingredients_by_category = {}
    category_labels = dict(INGREDIENT_CATEGORIES)

    if request.method == "POST":
        # Get selected week IDs from checkboxes
        selected_week_ids = request.POST.getlist("weeks")

        if selected_week_ids:
            # Fetch only non-skipped weeks
            selected_weeks = MealPlanWeek.objects.filter(
                pk__in=selected_week_ids,
                skipped=False,
                archived=False,
            )

            # All non-skipped meals in those weeks
            meals = (
                PlannedMeal.objects.filter(
                    week__in=selected_weeks,
                    skipped=False,
                )
                .select_related("recipe", "week")
                .prefetch_related("recipe__ingredients")
            )

            # Prepare structure: category -> list of items
            ingredients_by_category = {key: [] for key, _ in INGREDIENT_CATEGORIES}
            seen = set()  # avoid exact duplicates

            for meal in meals:
                for ing in meal.recipe.ingredients.all():
                    cat = ing.category
                    name = ing.name.strip()
                    amount = (ing.amount or "").strip()

                    key = (cat, name, amount)
                    if key in seen:
                        continue
                    seen.add(key)

                    if amount:
                        label = f"{amount} – {name}"
                    else:
                        label = name

                    if cat in ingredients_by_category:
                        ingredients_by_category[cat].append(label)
                    else:
                        # Fallback in case of unexpected category
                        ingredients_by_category.setdefault(cat, []).append(label)

    context = {
        "weeks": weeks,
        "selected_week_ids": selected_week_ids,
        "ingredients_by_category": ingredients_by_category,
        "category_labels": category_labels,
    }
    return render(request, "planner/shopping_list.html", context)

def shopping_list_pdf(request):
    if request.method != "POST":
        # PDF export only makes sense from the form submission
        return redirect("planner:shopping_list")

    # Items the user kept checked on the shopping list page
    raw_items = request.POST.getlist("items")

    # Weeks (used for PDF header and fallback behaviour)
    selected_week_ids = request.POST.getlist("weeks")
    selected_weeks = MealPlanWeek.objects.filter(
        pk__in=selected_week_ids
    ).order_by("start_date", "id")

    ingredients_by_category = {key: [] for key, _ in INGREDIENT_CATEGORIES}
    category_labels = dict(INGREDIENT_CATEGORIES)

    if raw_items:
        # Use the filtered items from the shopping-list page.
        # Each value is "category_key|||label"
        for raw in raw_items:
            try:
                cat_key, label = raw.split("|||", 1)
            except ValueError:
                # Ignore malformed values
                continue

            if cat_key in ingredients_by_category:
                ingredients_by_category[cat_key].append(label)
            else:
                ingredients_by_category.setdefault(cat_key, []).append(label)
    else:
        # Fallback: old behavior – recompute from the selected weeks
        if not selected_week_ids:
            # No weeks selected; send back to the normal page
            return redirect("planner:shopping_list")

        # Fetch only non-skipped weeks
        selected_weeks = MealPlanWeek.objects.filter(
            pk__in=selected_week_ids,
            skipped=False,
        ).order_by("start_date", "id")

        # All non-skipped meals in those weeks
        meals = (
            PlannedMeal.objects.filter(
                week__in=selected_weeks,
                skipped=False,
            )
            .select_related("recipe", "week")
            .prefetch_related("recipe__ingredients")
        )

        seen = set()  # avoid exact duplicates

        for meal in meals:
            for ing in meal.recipe.ingredients.all():
                cat = ing.category
                name = ing.name.strip()
                amount = (ing.amount or "").strip()

                key = (cat, name, amount)
                if key in seen:
                    continue
                seen.add(key)

                if amount:
                    label = f"{amount} – {name}"
                else:
                    label = name

                if cat in ingredients_by_category:
                    ingredients_by_category[cat].append(label)
                else:
                    ingredients_by_category.setdefault(cat, []).append(label)

    # Column layout for the PDF:
    # Left side: Produce, Protein, Frozen (your half)
    # Right side: Pantry, Dairy, plus any other categories
    left_categories = ["produce", "protein", "frozen"]
    right_categories = [key for key, _ in INGREDIENT_CATEGORIES if key not in left_categories]

    context = {
        "weeks": selected_weeks,
        "ingredients_by_category": ingredients_by_category,
        "category_labels": category_labels,
        "left_categories": left_categories,
        "right_categories": right_categories,
    }

    pdf_bytes = render_to_pdf("planner/shopping_list_pdf.html", context)
    if pdf_bytes is None:
        return HttpResponse("Error generating PDF", status=500)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="shopping_list.pdf"'
    return response


def recipe_pdf(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    pdf_bytes = render_to_pdf("planner/recipe_pdf.html", {"recipe": recipe})

    if pdf_bytes is None:
        return HttpResponse("Error generating PDF", status=500)

    filename = f"recipe_{recipe.pk}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

