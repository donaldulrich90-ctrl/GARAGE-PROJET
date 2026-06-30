from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExpenseForm
from .models import Expense


@login_required
def expense_list(request):
    if getattr(request.user, "garage", None) is None:
        return redirect("dashboard_home")
    qs = Expense.objects.for_garage(request.user.garage)

    category = request.GET.get("category", "")
    if category:
        qs = qs.filter(category=category)

    total = qs.aggregate(t=Sum("amount"))["t"] or 0
    categories = Expense.CATEGORY_CHOICES

    return render(request, "expenses/expense_list.html", {
        "expenses": qs,
        "total": total,
        "categories": categories,
        "selected_category": category,
    })


@login_required
def expense_create(request):
    if getattr(request.user, "garage", None) is None:
        return redirect("dashboard_home")
    if request.method == "POST":
        form = ExpenseForm(request.POST, garage=request.user.garage)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.garage = request.user.garage
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, "Dépense enregistrée.")
            return redirect("expense_list")
    else:
        form = ExpenseForm(garage=request.user.garage)
    return render(request, "expenses/expense_form.html", {"form": form, "action": "Enregistrer"})


@login_required
def expense_edit(request, pk):
    if getattr(request.user, "garage", None) is None:
        return redirect("dashboard_home")
    expense = get_object_or_404(Expense, pk=pk, garage=request.user.garage)
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense, garage=request.user.garage)
        if form.is_valid():
            form.save()
            messages.success(request, "Dépense mise à jour.")
            return redirect("expense_list")
    else:
        form = ExpenseForm(instance=expense, garage=request.user.garage)
    return render(request, "expenses/expense_form.html", {"form": form, "action": "Modifier", "expense": expense})


@login_required
def expense_delete(request, pk):
    if getattr(request.user, "garage", None) is None:
        return redirect("dashboard_home")
    expense = get_object_or_404(Expense, pk=pk, garage=request.user.garage)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Dépense supprimée.")
        return redirect("expense_list")
    return render(request, "expenses/expense_confirm_delete.html", {"expense": expense})
