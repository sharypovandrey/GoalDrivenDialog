from jinja2 import Environment, select_autoescape

class InputTemplate:
    env = Environment(
        autoescape=select_autoescape(
            enabled_extensions=("html", "xml"),
            default_for_string=False,
        ),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    def __init__(self, text, filters = {}):
        for filter_label, filter_function in filters.items():
            self.env.filters[filter_label] = filter_function
        self._template = self.env.from_string(text)

    def text(self, data):
        rendered: str = self._template.render(data)
        return rendered