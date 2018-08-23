
import re
import sys

from .common import REPLSyntaxError

class ExpandableString:
    def __init__(self, s = "", delimiter = "$"):
        self.__s = str(s)
        self.__delimiter = delimiter

    def __add__(self, s):
        return ExpandableString(self.__s + str(s))

    def __iadd__(self, s):
        self.__s += str(s)
        return self

    def __getitem__(self, key):
        return ExpandableString(self.__s[key])

    def __len__(self):
        return len(self.__s)

    def lstrip(self, *args, **kwargs):
        return self.__s.lstrip(*args, **kwargs)

    def rstrip(self, *args, **kwargs):
        return self.__s.rstrip(*args, **kwargs)

    def strip(self, *args, **kwargs):
        return self.__s.strip(*args, **kwargs)

    def expand(self, env):
        s = self.__s

        exploded = s.split("$")

        tokens, exploded = [exploded[0]], exploded[1:]

        if len(exploded) == 0: return s

        """
        Identifiers match one of the following regexes:
        $[A-Za-z_0-9?#@-][A-Za-z0-9_-]*
        ${[A-Za-z_0-9?#@-][A-Za-z0-9_-]*}
        """

        identifier = re.compile("([A-Za-z0-9_?#@-][A-Z-a-z0-9_-]*)")
        identifier2 = re.compile("{([A-Za-z0-9_?#@-][A-Za-z0-9_-]*)}")

        for debris in exploded:
            if len(debris) == 0:
                tokens.append("$")
                continue

            match = identifier.match(debris)
            match2 = identifier2.match(debris)

            match = match or match2

            if match is not None:
                identifier_ = match.group(1)
                tokens.append(env.get(identifier_))

            # Drop the rest of the string in
            if match is None:
                tokens.append("")
            elif match.end() < len(debris):
                tokens.append(debris[match.end():])

        """
        The semantics of ${} notation are left undefined and unimplemented
        here. We'll deal with parameter expansion in the future as needed.
        """

        return "".join(tokens)

    def quote(self):
        return '"{}"'.format(self.__s)

    def __repr__(self):
        return "ExpandableString({})".format(self.__s)

    def __str__(self):
        return self.__s

    def __eq__(self, rhs):
        return self.__s == rhs

class NonExpandableString:
    def __init__(self, s = ""):
            self.__s = str(s)

    def __add__(self, s):
        return NonExpandableString(self.__s + str(s))

    def __iadd__(self, s):
        self.__s += str(s)
        return self

    def __getitem__(self, key):
        return NonExpandableString(self.__s[key])

    def __len__(self):
        return len(self.__s)

    def expand(self, env):
        return self.__s

    def quote(self):
        return "'{}'".format(self.__s)
    def __repr__(self):

        return "NonExpandableString({})".format(self.__s)

    def __str__(self):
        return self.__s

    def __eq__(self, rhs):
        return self.__s == rhs

def quote(string):
    if type(string) == str:
        string = re.sub("(['\"])", r"\1", string)
        if any((c in string) for c in [" ", "#", "|"]):
            return '"{}"'.format(string)
        else:
            return string
    elif type(string) in [ExpandableString, NonExpandableString]:
        return string.quote()
    else:
        # This has been a disaster
        return string

def expand(string, bindings):
    if type(string) in [ExpandableString, NonExpandableString]:
        return string.expand(bindings)
    elif type(string) == str:
        return ExpandableString(string).expand(bindings)
    else: return string

def is_string_type(s):
    t = type(s)
    return t == str or t == ExpandableString or t == NonExpandableString

def escapes_next(prev):
    if not is_string_type(prev): return False

    if len(prev) == 0: return False

    return prev[-1] == "\\"

def acknowledge_escape(last):
    if len(last) > 0 and last[-1] != "\\":
        return last
    else: return last[:-1]

def merge_quotes(tokens):
    tokens_ = []
    acc = None
    last = None

    for t in tokens:
        if t == "": continue

        if acc is None:
            if t == "'" and not escapes_next(last):
                acc = NonExpandableString(str())
            elif t == '"' and not escapes_next(last):
                acc = ExpandableString(str())
            else:
                if t in ['"', "'"] and escapes_next(last):
                    tokens_[-1] = acknowledge_escape(tokens_[-1])
                tokens_.append(t)
        else:
            if t == "'" and type(acc) == NonExpandableString:
                if not escapes_next(last):
                    tokens_.append(acc)
                    acc = None
            elif t == '"' and type(acc) == ExpandableString:
                if not escapes_next(last):
                    tokens_.append(acc)
                    acc = None
            else:
                # Don't ask me why this works. I haven't figured that out yet
                if last in ['"', "'"] and escapes_next(acc):
                    acc = acknowledge_escape(acc)
                    acc += last
                acc = acc + t

        last = t

    if acc is not None:
        raise REPLSyntaxError("Unmatched quote")

    return tokens_

def merge_strings(tokens):

    if not tokens: return tokens

    _tokens = []

    acc = tokens[0]
    for t in tokens[1:]:
        if type(t) == str:
            acc = t if acc is None else acc + t
        else:
            _tokens.append(acc)
            acc = None
            _tokens.append(t)
    else:
        if acc is not None:
            _tokens.append(acc)

    tokens = _tokens

    return tokens

# Merge across escaped whitespace
def merge_whitespace(tokens):
    tokens_ = []

    for token in tokens:
        if type(token) != str:
            tokens_.append(token)
            continue

        pieces = re.split("""([ \t])""", token)
        escaped = False
        for bits in pieces:
            if bits == "": continue
            if bits == " " or bits == "\t":
                if len(tokens_) > 0 and escapes_next(tokens_[-1]):
                    escaped = True
                    tokens_[-1] = acknowledge_escape(tokens_[-1])
                    tokens_[-1] += bits
            else:
                if escaped:
                    tokens_[-1] += bits
                else:
                    tokens_.append(bits)

    tokens = tokens_

    return tokens

def break_character(tokens, character):
    if len(character) > 1:
        raise RuntimeError("Can only break on one character at a time:"
                + " {} is too many".format(character))

    tokens_ = []

    for token in tokens:
        # If quoted, they're not special, not present = nothing to do
        if type(token) != str or not character in token:
            tokens_.append(token)
            continue

        merge = False
        pieces = re.split("([{}])".format(character), token)
        for bits in pieces:
            if bits == "": continue
            # If it was escaped, merge it back in and continue
            # TODO - This doesn't work at all. We must side-effect the outer
            # loop, not this one
            if (bits == character
                and len(tokens_) > 0
                and escapes_next(tokens_[-1])):

                tokens_[-1] = tokens_[-1][:-1]
                tokens_[-1] += bits
                merge = True
                continue
            if not merge:
                tokens_.append(bits)
            elif merge and bits == character:
                tokens_.append(bits)
                merge = False
            else:
                tokens_[-1] += bits
                merge = False

    return tokens_

def discard_comments(tokens):
    tokens_ = []

    pieces = break_character(tokens, "#")

    last = "@"
    for bit in pieces:
        # Oof
        if type(bit) == str and bit == "#" and last[-1] != "$":
            break
        # Ouch
        elif last[-1] == "$" and bit == "#":
            tokens_[-1] += "#"
        else:
            tokens_.append(bit)
        last = bit

    return tokens_

def split_whitespace(string):
    """
    Split a string across whitespace, respecting quoting rules
    """

    """
    Split across all quotes, consuming the ones that we care about.
    If we know types of quote that we care about, it is possible to reproduce
    the original string.
    """

    tokens = re.split("""(['"])""", string)

    if len(tokens) > 1:
        tokens = merge_quotes(tokens)

    """
    Anything that was quoted is already merged correctly whitespace-wise, but
    every other string still needs to be merged before anything else can be
    done.
    Merge all runs of type str()
    """

    tokens = merge_strings(tokens)

    """
    Now we need to split all non-quoted strings over whitespace, and merge any
    that escape the whitespace
    """

    tokens = merge_whitespace(tokens)

    """
    We remove unquoted comments here, discarding them and anything following
    them
    """

    tokens = discard_comments(tokens)

    """
    Special character ` needs to be processed here. If there are any bare or
    unescaped ones, they need to be broken out.
    """

    tokens = break_character(tokens, "`")

    """
    Special character | must be processed here. If there are any bare or
    unescaped ones, they need to be broken out.
    """

    tokens = break_character(tokens, "|")

    """
    At this point, anything that isn't a NonExpandableString is semantically
    an expandable string, so let's clean up that loose end
    """

    return [ExpandableString(token) if type(token) is not NonExpandableString
            else token for token in tokens ]

