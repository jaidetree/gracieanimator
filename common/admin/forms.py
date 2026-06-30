"""Shared admin form pieces, reused across apps.

Lives in ``common`` (a plain importable package, not an installed app — it ships
no models, templates, or migrations) so any app's admin can pull in the same
WYSIWYG wiring without one app depending on another.
"""

from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget


class CKEditorBodyForm(forms.ModelForm):
    """A ``ModelForm`` whose ``body`` is the CKEditor 5 widget, themed to admin.

    Mixed into a concrete admin form that supplies its own ``Meta`` (model +
    fields). The widget lives on the form, not the model, so ``body`` stays a
    plain ``TextField`` (no migration) and the editor is an admin-only concern.
    ``body`` is declared explicitly so it carries the widget while the admin
    still builds the rest of the fieldset itself.

    This base has no ``Meta`` of its own, which is fine: Django only rejects a
    model-less ``ModelForm`` on *instantiation*, and the mixin is never
    instantiated directly.
    """

    body = forms.CharField(
        widget=CKEditor5Widget(config_name="default"), required=False
    )

    class Media:
        # Map CKEditor's palette onto the admin theme vars so the editor follows
        # the admin's light/dark/auto color mode (see the stylesheet). The path
        # is a static URL resolved against STATICFILES_DIRS, independent of where
        # this form class lives.
        css = {"all": ("admin/css/ckeditor5-dark.css",)}
