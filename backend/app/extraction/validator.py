from jsonschema import ValidationError, validate


def validate_json(data: dict, schema: dict) -> tuple[bool, str]:
    try:
        validate(instance=data, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, str(e)
