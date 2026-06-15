from django.contrib import admin
from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.admin import FlatPageAdmin as FlatPageAdminOld
from django import forms
from ckeditor.widgets import CKEditorWidget

# Cria um formulário personalizado utilizando o CKEditor no conteúdo
class FlatPageForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = FlatPage
        fields = '__all__'

# Sobrescreve a classe de administração
class FlatPageAdmin(FlatPageAdminOld):
    form = FlatPageForm

# Desregistra o FlatPage padrão e registra o novo
admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageAdmin)
