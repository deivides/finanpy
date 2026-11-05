from django import forms

INPUT_CLASS = 'form-input'
CHECKBOX_CLASS = 'h-4 w-4 accent-violet-500'
HTML5_DATE_FORMAT = '%Y-%m-%d'


class StyledFormMixin:
    """Apply the design system classes (PRD 9.6) to every form widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                self._add_css_class(widget, CHECKBOX_CLASS)
            else:
                self._add_css_class(widget, INPUT_CLASS)
            if isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
                # The browser only accepts ISO dates; the pt-BR default
                # (DATE_INPUT_FORMATS[0]) would render dd/mm/yyyy.
                if not widget.format:
                    widget.format = HTML5_DATE_FORMAT

    @staticmethod
    def _add_css_class(widget, css_class):
        classes = widget.attrs.get('class', '').split()
        for name in css_class.split():
            if name not in classes:
                classes.append(name)
        widget.attrs['class'] = ' '.join(classes)
