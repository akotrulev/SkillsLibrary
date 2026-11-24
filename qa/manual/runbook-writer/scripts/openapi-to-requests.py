"""Turns an OpenAPI 3 JSON document into a request catalogue, one file per tag: `curl` commands or `.http` requests."""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
PATH_PARAMETER = re.compile(r"\{([^{}]+)\}")
REQUEST_HEADING = re.compile(r"^### ", re.MULTILINE)
WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
SHELL_SPECIAL = re.compile(r'([\\"$`])')
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


@dataclass(frozen=True)
class Request:
    """One operation of the document, with everything a renderer needs to write it as a sendable request."""

    tag: str
    title: str
    summary: Optional[str]
    statuses: Tuple[str, ...]
    method: str
    path: str
    required_query: Tuple[str, ...]
    optional_query: Tuple[str, ...]
    headers: Tuple[str, ...]
    auth_kind: Optional[str]
    api_key_header: Optional[str]
    media_type: Optional[str]
    has_json_body: bool
    body: object

    @property
    def heading(self):
        return f"### {self.title} — {self.summary}" if self.summary else f"### {self.title}"

    @property
    def hand_written_body(self):
        return self.media_type if self.media_type and not self.has_json_body else None


def auth_scheme(document, operation):
    requirements = operation.get("security", document.get("security", []))
    if not requirements or not requirements[0]:
        return None, None
    name = next(iter(requirements[0]))
    scheme = document.get("components", {}).get("securitySchemes", {}).get(name, {})
    http_scheme = scheme.get("scheme", "").lower()
    if scheme.get("type") in BEARER_TYPES or http_scheme == "bearer":
        return "bearer", None
    if http_scheme == "basic":
        return "basic", None
    if scheme.get("type") == "apiKey" and scheme.get("in") == "header":
        return "apiKey", scheme["name"]
    return None, None


def describe(document, path, method, path_item, operation):
    declared = parameters(document, path_item, operation)
    content = resolve(document, operation.get("requestBody", {})).get("content", {})
    media_type = preferred_media_type(content)
    has_json_body = media_type is not None and is_json(media_type)
    auth_kind, api_key_header = auth_scheme(document, operation)
    return Request(
        tag=(operation.get("tags") or ["default"])[0],
        title=operation.get("operationId", f"{method.upper()} {path}"),
        summary=operation.get("summary"),
        statuses=tuple(operation.get("responses", {})),
        method=method.upper(),
        path=path,
        required_query=tuple(p["name"] for p in declared if p["in"] == "query" and p.get("required")),
        optional_query=tuple(p["name"] for p in declared if p["in"] == "query" and not p.get("required")),
        headers=tuple(p["name"] for p in declared if p["in"] == "header" and p.get("required")),
        auth_kind=auth_kind,
        api_key_header=api_key_header,
        media_type=media_type,
        has_json_body=has_json_body,
        body=body_sample(document, content[media_type]) if has_json_body else None,
    )


def file_stem(tag):
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def requests_by_file(document):
    """Groups the document's operations by the file their first tag names, in document order."""
    if not str(document.get("openapi", "")).startswith("3."):
        raise CatalogueError("not an OpenAPI 3 document; a Swagger 2.0 service must export OpenAPI 3")
    grouped = {}
    for path, raw_item in document.get("paths", {}).items():
        path_item = resolve(document, raw_item)
        for method in METHODS:
            if method in path_item:
                request = describe(document, path, method, path_item, path_item[method])
                grouped.setdefault(file_stem(request.tag), []).append(request)
    if not grouped:
        raise CatalogueError("the document holds no operation under `paths`")
    return grouped


def http_variable(name):
    return "{{" + name + "}}"


HTTP_AUTH = {
    "bearer": lambda request: "Authorization: Bearer {{token}}",
    "basic": lambda request: "Authorization: Basic {{user}} {{password}}",
    "apiKey": lambda request: f"{request.api_key_header}: {http_variable('apiKey')}",
}


def render_http(request):
    lines = [request.heading]
    if request.statuses:
        lines.append(f"# Responses: {', '.join(request.statuses)}")
    if request.optional_query:
        lines.append(f"# Optional query: {', '.join(request.optional_query)}")
    if request.hand_written_body:
        lines.append(f"# Body: {request.hand_written_body}, written by hand")
    path = PATH_PARAMETER.sub(r"{{\1}}", request.path)
    lines.append(f"{request.method} {http_variable('baseUrl')}{path}")
    lines.extend(
        f"    {'&' if index else '?'}{name}={http_variable(name)}" for index, name in enumerate(request.required_query)
    )
    if request.auth_kind:
        lines.append(HTTP_AUTH[request.auth_kind](request))
    lines.extend(f"{name}: {http_variable(name)}" for name in request.headers)
    if request.has_json_body:
        lines.extend([f"Content-Type: {request.media_type}", "", json.dumps(request.body, indent=2)])
    return "\n".join(lines)


def http_catalogue(document):
    """Returns `.http` files by name: requests a person sends from the editor, or `ijhttp` a file at a time."""
    return {
        f"{stem}.http": "\n\n".join(render_http(request) for request in requests) + "\n"
        for stem, requests in requests_by_file(document).items()
    }


def shell_variable(name):
    return "$" + re.sub(r"[^A-Za-z0-9]+", "_", WORD_BOUNDARY.sub("_", name)).strip("_").upper()


CURL_AUTH = {
    "bearer": lambda request: '-H "Authorization: Bearer $TOKEN"',
    "basic": lambda request: '-u "$API_USER:$API_PASSWORD"',
    "apiKey": lambda request: f'-H "{request.api_key_header}: $API_KEY"',
}


def render_curl(request):
    """Writes the request in the form a runbook's API step has: the response saved, the status printed."""
    query = "&".join(f"{name}={shell_variable(name)}" for name in request.required_query)
    path = PATH_PARAMETER.sub(lambda match: shell_variable(match.group(1)), request.path)
    url = f'"$BASE_URL{path}{"?" + query if query else ""}"'
    options = [CURL_AUTH[request.auth_kind](request)] if request.auth_kind else []
    options.extend(f'-H "{name}: {shell_variable(name)}"' for name in request.headers)
    if request.has_json_body:
        options.append(f'-H "Content-Type: {request.media_type}"')
    command = ["curl -sS " + ("" if request.method == "GET" else f"-X {request.method} ") + url]
    if options:
        command.append("  " + " ".join(options))
    if request.has_json_body:
        body = SHELL_SPECIAL.sub(r"\\\1", json.dumps(request.body, separators=(",", ":")))
        command.append(f'  -d "{body}"')
    saved_as = re.sub(r"[^A-Za-z0-9]+", "-", request.title).strip("-")
    command.append(f"  -o \"$OUT/{saved_as}.json\" -w '%{{http_code}}\\n'")

    lines = [request.heading]
    if request.statuses:
        lines.append(f"Responses: {', '.join(request.statuses)}")
    if request.optional_query:
        lines.append(f"Optional query: {', '.join(request.optional_query)}")
    if request.hand_written_body:
        lines.append(f"Body: {request.hand_written_body}, added by hand")
    lines.extend(["", "```bash", " \\\n".join(command), "```"])
    return "\n".join(lines)


def curl_catalogue(document, source, url):
    """Returns Markdown files by name: one `curl` command per operation, for an agent or a shell to send."""
    return {
        f"{stem}.md": "\n\n".join(
            [
                f"# {requests[0].tag} — API requests",
                f"Generated from `{source}` by `openapi-to-requests.py`. Regenerate it; never edit it.",
                f"Set `BASE_URL` (`{url}`), `OUT` (the folder responses are saved to) and the variables a request "
                "names. Copy a request and replace every sampled value.",
                *(render_curl(request) for request in requests),
            ]
        )
        + "\n"
        for stem, requests in requests_by_file(document).items()
    }


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
    print(f"{path}: {name} baseUrl = {url}")


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        prog="openapi-to-requests.py",
        description="Write a request catalogue from an OpenAPI 3 JSON document, one file per tag.",
    )
    parser.add_argument("source", help="the OpenAPI 3 JSON document: a file path or an http(s) URL")
    parser.add_argument("--out", required=True, help="the folder the catalogue is written to")
    parser.add_argument(
        "--format",
        choices=("curl", "http"),
        default="curl",
        help="curl: Markdown files of curl commands (default). http: .http files plus http-client.env.json",
    )
    parser.add_argument("--base-url", help="the API's base URL, when the document names none or another")
    parser.add_argument("--env", default="dev", help="http format: the environment name in http-client.env.json")
    return parser.parse_args(argv)


def main(argv):
    arguments = parse_arguments(argv)
    try:
        document = load_document(arguments.source)
        url = base_url(document, arguments.source, arguments.base_url)
        as_http = arguments.format == "http"
        catalogue = http_catalogue(document) if as_http else curl_catalogue(document, arguments.source, url)
    except (CatalogueError, OSError) as error:
        print(f"openapi-to-requests: {error}", file=sys.stderr)
        return 1
    folder = Path(arguments.out)
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in catalogue.items():
        (folder / name).write_text(text, encoding="utf-8")
        print(f"{folder / name}: {len(REQUEST_HEADING.findall(text))} requests")
    if as_http:
        write_environment(folder, arguments.env, url)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
