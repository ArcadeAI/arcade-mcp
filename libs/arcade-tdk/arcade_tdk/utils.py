def snake_to_pascal_case(name: str) -> str:
    """
    Converts a snake_case name to PascalCase.
    """
    if "_" in name:
        return "".join(x.capitalize() or "_" for x in name.split("_"))
    # check if first letter is uppercase
    if name[0].isupper():
        return name
    return name.capitalize()
