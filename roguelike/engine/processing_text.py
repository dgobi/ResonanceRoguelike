"""The bounded preparation completion template shared by authoring and runtime."""
from string import Formatter


def validate_completion_template(template):
    if not isinstance(template, str):
        raise ValueError("Expected literal text with optional {item_name} and escaped braces.")
    for _, field, spec, conversion in Formatter().parse(template):
        if field is not None and (field != "item_name" or spec or conversion):
            raise ValueError("Only {item_name} is supported, without access, conversion or formatting.")
    # Empty format specifications also have to be refused; Formatter collapses
    # {item_name:} into the same parsed spec as {item_name}.
    remainder = template.replace("{{", "").replace("}}", "")
    if "{item_name:" in remainder:
        raise ValueError("Format specifications are unsupported.")


def completion_text(template, item_name):
    try:
        validate_completion_template(template)
        return template.format(item_name=item_name)
    except ValueError:
        return f"{item_name} is ready."
