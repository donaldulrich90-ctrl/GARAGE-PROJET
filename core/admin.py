class TenantScopedAdmin:
    """
    Mixin pour ModelAdmin : un superuser (staff plateforme) voit tout,
    un utilisateur garage ne voit/édite que les données de son garage.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(garage=request.user.garage)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not obj.garage_id:
            obj.garage = request.user.garage
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if not request.user.is_superuser and db_field.name == "garage" and formfield:
            formfield.initial = request.user.garage
            formfield.disabled = True
        return formfield
