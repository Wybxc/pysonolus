anonymous_variable_counter = 0


def anonymous():
    """Generate a name for an anonymous variable."""
    global anonymous_variable_counter
    anonymous_variable_counter += 1
    return f"${anonymous_variable_counter}"


__all__ = ['anonymous']
