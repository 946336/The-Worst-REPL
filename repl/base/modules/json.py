
from .. import command
import json

def commands():
    return [
        make_json_object_command(),
        make_json_list_command(),
        make_json_get_command(),
        make_json_set_command(),
        make_json_is_list_command(),
        make_json_list_append_command(),
        make_json_list_pop_command(),
        make_json_list_get_command(),
        make_json_list_set_command(),
        make_json_is_object_command(),
    ]

def make_json_object_command():
    def json_object():
        print("{}")
        return 0

    return command.Command(
        json_object,
        "json-object",
        "json-object",
        "Create an empty JSON object"
    )

def make_json_list_command():
    def json_list():
        print("[]")
        return 0

    return command.Command(
        json_list,
        "json-list",
        "json-list",
        "Create an empty JSON list"
    )

def make_json_list_append_command():
    def json_list_append(json_string, value):
        try:
            j = json.loads(json_string)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        if type(j) != list:
            print("Not a list!")
            return 3

        j.append(json.loads(value))

        print(json.dumps(j))
        return 0

    return command.Command(
        json_list_append,
        "json-list-append",
        "json-list-append json-string value",
        "Append a value to a JSON list"
    )

def make_json_list_pop_command():
    def json_list_pop():
        try:
            j = json.loads(json_string)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        if type(j) != list:
            print("Not a list!")
            return 3

        j.pop()

        print(json.dumps(j))
        return 0

    return command.Command(
        json_list_pop,
        "json-list-pop",
        "json-list-pop json-string",
        "Pop a value off of a JSON list"
    )

def make_json_list_set_command():
    def json_list_set(json_string, index, value):
        try:
            j = json.loads(json_string)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        if type(j) != list:
            print("Not a list!")
            return 3

        try:
            j[json.loads(index)] = json.loads(value)
        except KeyError as e:
            print("JSON list does not have index {}".format(index))
            return 2

        print(json.dumps(j))
        return 0

    return command.Command(
        json_list_set,
        "json-list-set",
        "json-list-set json-string index value",
        "Assign to an index in a JSON list"
    )

def make_json_list_get_command():
    def json_list_get(json_string, index, value):
        try:
            j = json.loads(json_string)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        if type(j) != list:
            print("Not a list!")
            return 3

        try:
            print(j[json.loads(index)])
        except KeyError as e:
            print("JSON list does not have index {}".format(index))
            return 2

        return 0

    return command.Command(
        json_list_get,
        "json-list-get",
        "json-list-get json-string index",
        "Extract a value at an index from a JSON list"
    )

def make_json_get_command():
    def json_get(json_str, *jpath):
        try:
            finger = json.loads(json_str)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        try:
            for selector in jpath:
                last = selector
                finger = finger[json.loads(selector)]
        except KeyError as e:
            print("Field {} not found".format(last))
            return 2
        else:
            print(json.dumps(finger))
            return 0

    return command.Command(
        json_get,
        "json-get",
        "json-get json-string selector [selectors...]",
        "Select fields from JSON objects"
    )

def make_json_set_command():
    def json_set(json_str, key, value):
        try:
            j = json.loads(json_str)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        j[str(key)] = json.loads(value)

        print(json.dumps(j))
        return 0

    return command.Command(
        json_set,
        "json-set",
        "json-set json-string field value",
        "Set a field in a JSON object"
    )

def make_json_is_list_command():
    def json_is_list(json_string):
        try:
            j = json.loads(json_string)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        return type(j) == list

    return command.Command(
        json_is_list,
        "json-is-list",
        "json-is-list json-string",
        "Determine if json-string represents a list"
    )

def make_json_is_object_command():
    def json_is_object(json_string):
        try:
            j = json.loads(json_string)
        except json.JSONDecodeError as e:
            print("Malformed JSON")
            return 2

        return type(j) == dict

    return command.Command(
        json_is_object,
        "json-is-object",
        "json-is-object json-string",
        "Determine if json-string represents an object"
    )
