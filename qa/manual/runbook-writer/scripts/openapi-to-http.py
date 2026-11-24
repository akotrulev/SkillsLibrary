"""Turns an OpenAPI 3 JSON document into a catalogue of `.http` request files, one per tag."""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
PATH_PARAMETER = re.compile(r"\{([^{}]+)\}")
REQUEST_HEADING = re.compile(r"^### ", re.MULTILINE)
STRING_SAMPLES = {
    "date-time": "2026-01-01T00:00:00Z",
    "date": "2026-01-01",
    "uuid": "00000000-0000-0000-0000-000000000000",
    "email": "user@example.test",
    "uri": "https://example.test",
}
SCALAR_SAMPLES = {"integer": 0, "number": 0, "boolean": False}
BEARER_TYPES = ("oauth2", "openIdConnect")
ENVIRONMENT_FILE = "http-client.env.json"


class CatalogueError(Exception):
    """A document the catalogue cannot be built from; its message is shown to the user as it is."""


def is_url(text):
    return urllib.parse.urlparse(text).scheme in ("http", "https")


def load_document(source):
    if is_url(source):
        with urllib.request.urlopen(source, timeout=30) as response:
            text = response.read().decode("utf-8")
    else:
        text = Path(source).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise CatalogueError(
            f"{source} is not JSON ({error.msg} at line {error.lineno}); export a YAML document as JSON"
        ) from error


def lookup(document, pointer):
    if not pointer.startswith("#/"):
        raise CatalogueError(f"only references inside the document are supported: {pointer}")
    target = document
    for escaped in pointer[2:].split("/"):
        key = escaped.replace("~1", "/").replace("~0", "~")
        if key not in target:
            raise CatalogueError(f"reference not found in the document: {pointer}")
        target = target[key]
    return target


def resolve(document, node):
    while "$ref" in node:
        node = lookup(document, node["$ref"])
    return node


def schema_type(schema):
    declared = schema.get("type")
    if isinstance(declared, list):
        named = [name for name in declared if name != "null"]
        return named[0] if named else None
    if declared is None and "properties" in schema:
        return "object"
    return declared


def sample(document, schema, open_references=frozenset()):
    """Builds one value a schema accepts. A reference already being sampled yields None, which ends a cycle."""
    pointer = schema.get("$ref")
    if pointer in open_references:
        return None
    if pointer:
        return sample(document, lookup(document, pointer), open_references | {pointer})
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if schema.get("enum"):
        return schema["enum"][0]
    if "allOf" in schema:
        own = {key: value for key, value in schema.items() if key != "allOf"}
        parts = [sample(document, part, open_references) for part in [*schema["allOf"], own]]
        merged = {}
        for part in parts:
            merged.update(part if isinstance(part, dict) else {})
        return merged
    alternatives = [option for option in [*schema.get("oneOf", []), *schema.get("anyOf", [])] if option.get("type") != "null"]
    if alternatives:
        return sample(document, alternatives[0], open_references)
    kind = schema_type(schema)
    if kind == "object":
        return {
            name: sample(document, member, open_references)
            for name, member in schema.get("properties", {}).items()
            if not member.get("readOnly")
        }
    if kind == "array":
        return [sample(document, schema.get("items", {}), open_references)]
    if kind == "string":
        return STRING_SAMPLES.get(schema.get("format"), "string")
    return SCALAR_SAMPLES.get(kind)


def is_json(media_type):
    return media_type == "application/json" or media_type.endswith("+json")


def preferred_media_type(content):
    json_types = [media_type for media_type in content if is_json(media_type)]
    return next(iter(json_types or content), None)


def body_sample(document, media):
    if "example" in media:
        return media["example"]
    if media.get("examples"):
        return resolve(document, next(iter(media["examples"].values()))).get("value")
    return sample(document, media.get("schema", {}))


def parameters(document, path_item, operation):
    merged = {}
    for raw in [*path_item.get("parameters", []), *operation.get("parameters", [])]:
        parameter = resolve(document, raw)
        merged[(parameter["name"], parameter["in"])] = parameter
    return list(merged.values())


def auth_header(document, operation):
    requirements = operation.get("security", document.get("security", []))
    if not requirements or not requirements[0]:
        return None
    name = next(iter(requirements[0]))
    scheme = document.get("components", {}).get("securitySchemes", {}).get(name, {})
    http_scheme = scheme.get("scheme", "").lower()
    if scheme.get("type") in BEARER_TYPES or http_scheme == "bearer":
        return "Authorization: Bearer {{token}}"
    if http_scheme == "basic":
        return "Authorization: Basic {{user}} {{password}}"
    if scheme.get("type") == "apiKey" and scheme.get("in") == "header":
        return f"{scheme['name']}: {{{{apiKey}}}}"
    return None


def variable(name):
    return "{{" + name + "}}"


def render_operation(document, path, method, path_item, operation):
    declared = parameters(document, path_item, operation)
    required_query = [p["name"] for p in declared if p["in"] == "query" and p.get("required")]
    optional_query = [p["name"] for p in declared if p["in"] == "query" and not p.get("required")]
    required_headers = [p["name"] for p in declared if p["in"] == "header" and p.get("required")]
    content = resolve(document, operation.get("requestBody", {})).get("content", {})
    media_type = preferred_media_type(content)
    sampled = media_type is not None and is_json(media_type)
    title = operation.get("operationId", f"{method.upper()} {path}")
    summary = operation.get("summary")
    statuses = ", ".join(operation.get("responses", {}))
    authorization = auth_header(document, operation)
    url_path = PATH_PARAMETER.sub(r"{{\1}}", path)

    lines = [f"### {title} — {summary}" if summary else f"### {title}"]
    if statuses:
        lines.append(f"# Responses: {statuses}")
    if optional_query:
        lines.append(f"# Optional query: {', '.join(optional_query)}")
    if media_type and not sampled:
        lines.append(f"# Body: {media_type}, written by hand")
    lines.append(f"{method.upper()} {variable('baseUrl')}{url_path}")
    lines.extend(
        f"    {'&' if index else '?'}{name}={variable(name)}" for index, name in enumerate(required_query)
    )
    if authorization:
        lines.append(authorization)
    lines.extend(f"{name}: {variable(name)}" for name in required_headers)
    if media_type:
        lines.append(f"Content-Type: {media_type}")
    if sampled:
        lines.extend(["", json.dumps(body_sample(document, content[media_type]), indent=2)])
    return "\n".join(lines)


def file_name(tag):
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-") + ".http"


def build_catalogue(document):
    """Returns the catalogue as file name to file text, one file per tag, operations in document order."""
    if not str(document.get("openapi", "")).startswith("3."):
        raise CatalogueError("not an OpenAPI 3 document; a Swagger 2.0 service must export OpenAPI 3")
    requests_by_file = {}
    for path, raw_item in document.get("paths", {}).items():
        path_item = resolve(document, raw_item)
        for method in METHODS:
            if method in path_item:
                operation = path_item[method]
                tag = (operation.get("tags") or ["default"])[0]
                request = render_operation(document, path, method, path_item, operation)
                requests_by_file.setdefault(file_name(tag), []).append(request)
    if not requests_by_file:
        raise CatalogueError("the document holds no operation under `paths`")
    return {name: "\n\n".join(requests) + "\n" for name, requests in requests_by_file.items()}


def base_url(document, source, override):
    if override:
        return override.rstrip("/")
    servers = document.get("servers", [])
    declared = servers[0]["url"] if servers else ""
    resolved = urllib.parse.urljoin(source, declared or "/") if is_url(source) else declared
    if not is_url(resolved):
        raise CatalogueError("the document names no absolute server URL; pass --base-url")
    return resolved.rstrip("/")


def write_environment(folder, name, url):
    """Sets `baseUrl` for one environment and keeps every other entry a person added to the file."""
    path = folder / ENVIRONMENT_FILE
    environments = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    environments[name] = {**environments.get(name, {}), "baseUrl": url}
    path.write_text(json.dumps(environments, indent=2) + "\n", encoding="utf-8")


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        prog="openapi-to-http.py",
        description="Write one .http file per tag of an OpenAPI 3 JSON document, plus http-client.env.json.",
    )
    parser.add_argument("source", help="the OpenAPI 3 JSON document: a file path or an http(s) URL")
    parser.add_argument("--out", required=True, help="the folder the catalogue is written to")
    parser.add_argument("--env", default="dev", help="the environment name in http-client.env.json (default: dev)")
    parser.add_argument("--base-url", help="the API's base URL, when the document names none or another")
    return parser.parse_args(argv)


def main(argv):
    arguments = parse_arguments(argv)
    try:
        document = load_document(arguments.source)
        catalogue = build_catalogue(document)
        url = base_url(document, arguments.source, arguments.base_url)
    except (CatalogueError, OSError) as error:
        print(f"openapi-to-http: {error}", file=sys.stderr)
        return 1
    folder = Path(arguments.out)
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in catalogue.items():
        (folder / name).write_text(text, encoding="utf-8")
        print(f"{folder / name}: {len(REQUEST_HEADING.findall(text))} requests")
    write_environment(folder, arguments.env, url)
    print(f"{folder / ENVIRONMENT_FILE}: {arguments.env} baseUrl = {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
