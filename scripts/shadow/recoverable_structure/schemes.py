ALLOWED_SCHEMES = frozenset({"positional", "type_slot"})


class UnknownScheme(ValueError):
    pass


def validate_schemes(names):
    names = list(names)
    if not names or len(names) > 2:
        raise UnknownScheme("role_schemes must have 1 or 2 entries")
    extra = [n for n in names if n not in ALLOWED_SCHEMES]
    if extra:
        raise UnknownScheme(f"forbidden role scheme(s): {extra}")
    if len(set(names)) != len(names):
        raise UnknownScheme("duplicate role scheme")
    return names


def role_ids(scheme, length, type_tags):
    if scheme == "positional":
        return list(range(length))
    if scheme == "type_slot":
        if type_tags is None or len(type_tags) != length:
            raise UnknownScheme("type_slot requires type_tags of span length")
        table = {"TOKEN": 0, "SLOT": 1, "MARKER": 2}
        out = []
        for tag in type_tags:
            if tag not in table:
                raise UnknownScheme(f"unknown type tag: {tag}")
            out.append(table[tag])
        return out
    raise UnknownScheme(scheme)


def n_roles(scheme, max_len):
    if scheme == "positional":
        return max_len
    if scheme == "type_slot":
        return 3
    raise UnknownScheme(scheme)
