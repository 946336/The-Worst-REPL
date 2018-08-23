
indent = [
        "function",
        "while",
        "if",
        "elif",
        "else",
        ]

dedent = [
        "elif",
        "else",
        "endif",
        "endfunction",
        "done",
        ]

def format(code, depth = 0, indent_size = 4):
    if not code: return code

    formatted = []
    for line in code:

        if any([line.strip().startswith(keyword) for keyword in dedent]):
            depth -= 1
            depth = 0 if depth < 0 else depth

        line = " " * depth * indent_size + line.strip()
        formatted.append(line)

        if any([line.strip().startswith(keyword) for keyword in indent]):
            depth += 1

    return "\n".join(formatted)

