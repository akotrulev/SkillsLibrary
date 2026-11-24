import contextlib
import importlib.util
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("openapi_to_http", HERE / "openapi-to-http.py")
openapi_to_http = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(openapi_to_http)

BEARER = {"type": "http", "scheme": "bearer"}


def a_document(paths, **members):
    return {"openapi": "3.0.3", "paths": paths, **members}


def a_secured_document(scheme, operation_members=None):
    operation = {"operationId": "listOrders", **(operation_members or {})}
    return a_document(
        {"/orders": {"get": operation}},
        security=[{"main": []}],
        components={"securitySchemes": {"main": scheme}},
    )


def a_document_with_body(schema, schemas=None):
    operation = {"operationId": "createOrder", "requestBody": {"content": {"application/json": {"schema": schema}}}}
    return a_document({"/orders": {"post": operation}}, components={"schemas": schemas or {}})


def the_only_file(document):
    catalogue = openapi_to_http.build_catalogue(document)
    return catalogue[next(iter(catalogue))]


def the_body(document):
    return json.loads(the_only_file(document).split("\n\n", 1)[1])


class RequestLineTests(unittest.TestCase):
    def test_should_write_the_whole_request_when_the_operation_declares_every_part(self):
        document = a_document(
            {
                "/api/products/{id}": {
                    "put": {
                        "tags": ["Products"],
                        "operationId": "updateProduct",
                        "summary": "Update a product",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True},
                            {"name": "dryRun", "in": "query"},
                            {"name": "version", "in": "query", "required": True},
                            {"name": "tenant", "in": "query", "required": True},
                            {"name": "X-Request-Id", "in": "header", "required": True},
                            {"name": "X-Trace", "in": "header"},
                        ],
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"sku": {"type": "string"}}}}}},
                        "responses": {"200": {}, "404": {}},
                    }
                }
            },
            security=[{"main": []}],
            components={"securitySchemes": {"main": BEARER}},
        )

        catalogue = openapi_to_http.build_catalogue(document)

        self.assertEqual(
            catalogue,
            {
                "products.http": "### updateProduct — Update a product\n"
                "# Responses: 200, 404\n"
                "# Optional query: dryRun\n"
                "PUT {{baseUrl}}/api/products/{{id}}\n"
                "    ?version={{version}}\n"
                "    &tenant={{tenant}}\n"
                "Authorization: Bearer {{token}}\n"
                "X-Request-Id: {{X-Request-Id}}\n"
                "Content-Type: application/json\n"
                "\n"
                '{\n  "sku": "string"\n}\n'
            },
        )

    def test_should_title_the_request_by_method_and_path_when_the_operation_has_no_id(self):
        document = a_document({"/health": {"get": {}}})

        self.assertEqual(the_only_file(document), "### GET /health\nGET {{baseUrl}}/health\n")

    def test_should_keep_document_order_and_separate_requests_when_a_path_has_two_operations(self):
        document = a_document({"/orders": {"post": {"operationId": "create"}, "get": {"operationId": "list"}}})

        self.assertEqual(
            the_only_file(document),
            "### list\nGET {{baseUrl}}/orders\n\n### create\nPOST {{baseUrl}}/orders\n",
        )

    def test_should_merge_path_parameters_when_the_operation_overrides_one(self):
        document = a_document(
            {
                "/orders": {
                    "parameters": [{"name": "page", "in": "query"}, {"$ref": "#/components/parameters/Size"}],
                    "get": {"operationId": "list", "parameters": [{"name": "page", "in": "query", "required": True}]},
                }
            },
            components={"parameters": {"Size": {"name": "size", "in": "query"}}},
        )

        self.assertEqual(
            the_only_file(document),
            "### list\n# Optional query: size\nGET {{baseUrl}}/orders\n    ?page={{page}}\n",
        )

    def test_should_follow_the_reference_when_a_path_item_is_one(self):
        document = a_document(
            {"/orders": {"$ref": "#/components/pathItems/Orders"}},
            components={"pathItems": {"Orders": {"get": {"operationId": "list"}}}},
        )

        self.assertEqual(the_only_file(document), "### list\nGET {{baseUrl}}/orders\n")


class FileTests(unittest.TestCase):
    def test_should_write_one_file_per_tag_when_operations_carry_different_tags(self):
        document = a_document(
            {
                "/orders": {"get": {"tags": ["Order Admin"]}},
                "/users": {"get": {"tags": ["Users", "Other"]}},
                "/health": {"get": {"tags": []}},
                "/version": {"get": {}},
            }
        )

        catalogue = openapi_to_http.build_catalogue(document)

        self.assertEqual(sorted(catalogue), ["default.http", "order-admin.http", "users.http"])

    def test_should_share_a_file_when_two_tags_have_the_same_file_name(self):
        document = a_document({"/a": {"get": {"tags": ["Order Admin"]}}, "/b": {"get": {"tags": ["order-admin"]}}})

        catalogue = openapi_to_http.build_catalogue(document)

        self.assertEqual(
            catalogue,
            {"order-admin.http": "### GET /a\nGET {{baseUrl}}/a\n\n### GET /b\nGET {{baseUrl}}/b\n"},
        )

    def test_should_refuse_when_the_document_is_swagger_2(self):
        with self.assertRaisesRegex(openapi_to_http.CatalogueError, "not an OpenAPI 3 document"):
            openapi_to_http.build_catalogue({"swagger": "2.0", "paths": {"/a": {"get": {}}}})

    def test_should_refuse_when_the_document_holds_no_operation(self):
        with self.assertRaisesRegex(openapi_to_http.CatalogueError, "no operation"):
            openapi_to_http.build_catalogue(a_document({"/a": {"description": "empty"}}))


class AuthorizationTests(unittest.TestCase):
    def test_should_send_a_bearer_token_when_the_scheme_is_oauth2(self):
        document = a_secured_document({"type": "oauth2"})

        self.assertIn("\nAuthorization: Bearer {{token}}\n", the_only_file(document))

    def test_should_send_basic_credentials_when_the_scheme_is_http_basic(self):
        document = a_secured_document({"type": "http", "scheme": "Basic"})

        self.assertIn("\nAuthorization: Basic {{user}} {{password}}\n", the_only_file(document))

    def test_should_send_the_named_header_when_the_scheme_is_an_api_key_header(self):
        document = a_secured_document({"type": "apiKey", "in": "header", "name": "X-Api-Key"})

        self.assertIn("\nX-Api-Key: {{apiKey}}\n", the_only_file(document))

    def test_should_send_no_authorization_when_the_api_key_travels_in_the_query(self):
        document = a_secured_document({"type": "apiKey", "in": "query", "name": "key"})

        self.assertEqual(the_only_file(document), "### listOrders\nGET {{baseUrl}}/orders\n")

    def test_should_send_no_authorization_when_the_operation_clears_security(self):
        document = a_secured_document(BEARER, {"security": []})

        self.assertEqual(the_only_file(document), "### listOrders\nGET {{baseUrl}}/orders\n")

    def test_should_send_no_authorization_when_the_first_requirement_is_anonymous(self):
        document = a_secured_document(BEARER, {"security": [{}, {"main": []}]})

        self.assertEqual(the_only_file(document), "### listOrders\nGET {{baseUrl}}/orders\n")

    def test_should_send_no_authorization_when_the_scheme_is_not_declared(self):
        document = a_document({"/orders": {"get": {"operationId": "listOrders", "security": [{"missing": []}]}}})

        self.assertEqual(the_only_file(document), "### listOrders\nGET {{baseUrl}}/orders\n")


class BodyTests(unittest.TestCase):
    def test_should_sample_every_member_when_the_schema_is_a_referenced_object(self):
        document = a_document_with_body(
            {"$ref": "#/components/schemas/Order"},
            {
                "Order": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid", "readOnly": True},
                        "reference": {"type": "string"},
                        "placedAt": {"type": "string", "format": "date-time"},
                        "quantity": {"type": "integer"},
                        "total": {"type": "number"},
                        "gift": {"type": "boolean"},
                        "status": {"enum": ["Open", "Closed"]},
                        "currency": {"type": "string", "default": "EUR"},
                        "note": {"type": "string", "example": "Leave at the door"},
                        "lines": {"type": "array", "items": {"$ref": "#/components/schemas/Line"}},
                        "tags": {"type": "array"},
                        "anything": {},
                    },
                },
                "Line": {"properties": {"sku": {"type": "string"}}},
            },
        )

        self.assertEqual(
            the_body(document),
            {
                "reference": "string",
                "placedAt": "2026-01-01T00:00:00Z",
                "quantity": 0,
                "total": 0,
                "gift": False,
                "status": "Open",
                "currency": "EUR",
                "note": "Leave at the door",
                "lines": [{"sku": "string"}],
                "tags": [None],
                "anything": None,
            },
        )

    def test_should_merge_the_parts_when_the_schema_is_an_all_of(self):
        document = a_document_with_body(
            {
                "allOf": [{"$ref": "#/components/schemas/Base"}, {"type": "string"}],
                "properties": {"extra": {"type": "integer"}},
            },
            {"Base": {"type": "object", "properties": {"name": {"type": "string"}}}},
        )

        self.assertEqual(the_body(document), {"name": "string", "extra": 0})

    def test_should_take_the_first_alternative_that_is_not_null_when_the_schema_is_a_one_of(self):
        document = a_document_with_body(
            {"type": "object", "properties": {"owner": {"oneOf": [{"type": "null"}, {"type": "integer"}]}, "nick": {"anyOf": [{"type": "string"}]}}}
        )

        self.assertEqual(the_body(document), {"owner": 0, "nick": "string"})

    def test_should_take_the_named_type_when_the_type_is_a_list(self):
        document = a_document_with_body(
            {"type": "object", "properties": {"count": {"type": ["null", "integer"]}, "nothing": {"type": ["null"]}}}
        )

        self.assertEqual(the_body(document), {"count": 0, "nothing": None})

    def test_should_end_the_cycle_when_a_schema_refers_to_itself(self):
        document = a_document_with_body(
            {"$ref": "#/components/schemas/Node"},
            {"Node": {"type": "object", "properties": {"name": {"type": "string"}, "parent": {"$ref": "#/components/schemas/Node"}}}},
        )

        self.assertEqual(the_body(document), {"name": "string", "parent": None})

    def test_should_use_the_media_example_when_the_content_carries_one(self):
        document = a_document(
            {"/orders": {"post": {"requestBody": {"content": {"application/json": {"example": {"reference": "A-1"}, "schema": {"type": "string"}}}}}}}
        )

        self.assertEqual(the_body(document), {"reference": "A-1"})

    def test_should_use_the_first_named_example_when_the_content_carries_several(self):
        document = a_document(
            {"/orders": {"post": {"requestBody": {"content": {"application/json": {"examples": {"small": {"$ref": "#/components/examples/Small"}}}}}}}},
            components={"examples": {"Small": {"value": {"reference": "S-1"}}}},
        )

        self.assertEqual(the_body(document), {"reference": "S-1"})

    def test_should_prefer_the_json_content_when_the_body_offers_several_types(self):
        document = a_document(
            {
                "/orders": {
                    "post": {
                        "requestBody": {
                            "$ref": "#/components/requestBodies/Order",
                        }
                    }
                }
            },
            components={
                "requestBodies": {
                    "Order": {"content": {"application/xml": {}, "application/merge-patch+json": {"schema": {"type": "boolean"}}}}
                }
            },
        )

        self.assertEqual(
            the_only_file(document),
            "### POST /orders\nPOST {{baseUrl}}/orders\nContent-Type: application/merge-patch+json\n\nfalse\n",
        )

    def test_should_leave_the_body_to_the_tester_when_no_content_is_json(self):
        document = a_document({"/files": {"post": {"requestBody": {"content": {"multipart/form-data": {}}}}}})

        self.assertEqual(
            the_only_file(document),
            "### POST /files\n# Body: multipart/form-data, written by hand\nPOST {{baseUrl}}/files\nContent-Type: multipart/form-data\n",
        )

    def test_should_refuse_when_a_reference_leaves_the_document(self):
        document = a_document_with_body({"$ref": "other.json#/Order"})

        with self.assertRaisesRegex(openapi_to_http.CatalogueError, "only references inside the document"):
            openapi_to_http.build_catalogue(document)

    def test_should_refuse_when_a_reference_names_nothing(self):
        document = a_document_with_body({"$ref": "#/components/schemas/Missing~1Name"})

        with self.assertRaisesRegex(openapi_to_http.CatalogueError, "reference not found"):
            openapi_to_http.build_catalogue(document)


class BaseUrlTests(unittest.TestCase):
    def test_should_use_the_override_when_one_is_given(self):
        url = openapi_to_http.base_url({"servers": [{"url": "https://a.example.test"}]}, "openapi.json", "https://b.example.test/")

        self.assertEqual(url, "https://b.example.test")

    def test_should_use_the_first_server_when_it_is_absolute(self):
        url = openapi_to_http.base_url({"servers": [{"url": "https://a.example.test/v1/"}]}, "openapi.json", None)

        self.assertEqual(url, "https://a.example.test/v1")

    def test_should_join_the_server_to_the_source_when_the_server_is_relative(self):
        url = openapi_to_http.base_url({"servers": [{"url": "/v1"}]}, "https://a.example.test/swagger/v1/swagger.json", None)

        self.assertEqual(url, "https://a.example.test/v1")

    def test_should_use_the_origin_of_the_source_when_the_document_names_no_server(self):
        url = openapi_to_http.base_url({}, "https://a.example.test/swagger/v1/swagger.json", None)

        self.assertEqual(url, "https://a.example.test")

    def test_should_refuse_when_a_file_names_no_absolute_server(self):
        with self.assertRaisesRegex(openapi_to_http.CatalogueError, "pass --base-url"):
            openapi_to_http.base_url({"servers": [{"url": "/v1"}]}, "openapi.json", None)


class DocumentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = json.dumps(a_document({"/orders": {"get": {"operationId": "list"}}})).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


class CommandLine:
    """Runs the script's `main` in a folder of its own and keeps what it printed."""

    def __init__(self, folder):
        self.folder = folder
        self.out = folder / "requests"
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def run(self, *argv):
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return openapi_to_http.main(list(argv))

    def document_file(self, text):
        path = self.folder / "openapi.json"
        path.write_text(text, encoding="utf-8")
        return str(path)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.command_line = CommandLine(Path(directory.name))
        self.out = self.command_line.out

    def test_should_write_the_catalogue_and_the_environment_when_the_source_is_a_file(self):
        source = self.command_line.document_file(json.dumps(a_document({"/orders": {"get": {"tags": ["Orders"]}}}, servers=[{"url": "https://a.example.test"}])))

        code = self.command_line.run(source, "--out", str(self.out), "--env", "staging")

        self.assertEqual(
            (code, sorted(p.name for p in self.out.iterdir()), json.loads((self.out / "http-client.env.json").read_text())),
            (0, ["http-client.env.json", "orders.http"], {"staging": {"baseUrl": "https://a.example.test"}}),
        )

    def test_should_report_each_file_with_its_request_count_when_it_succeeds(self):
        source = self.command_line.document_file(json.dumps(a_document({"/orders": {"get": {}, "post": {}}})))

        self.command_line.run(source, "--out", str(self.out), "--base-url", "https://a.example.test")

        self.assertEqual(
            self.command_line.stdout.getvalue(),
            f"{self.out / 'default.http'}: 2 requests\n{self.out / 'http-client.env.json'}: dev baseUrl = https://a.example.test\n",
        )

    def test_should_keep_what_a_person_added_when_the_environment_file_exists(self):
        source = self.command_line.document_file(json.dumps(a_document({"/orders": {"get": {}}})))
        self.out.mkdir()
        (self.out / "http-client.env.json").write_text('{"dev": {"baseUrl": "old", "tenant": "t1"}, "uat": {"baseUrl": "u"}}')

        self.command_line.run(source, "--out", str(self.out), "--base-url", "https://a.example.test")

        self.assertEqual(
            json.loads((self.out / "http-client.env.json").read_text()),
            {"dev": {"baseUrl": "https://a.example.test", "tenant": "t1"}, "uat": {"baseUrl": "u"}},
        )

    def test_should_read_the_document_over_http_when_the_source_is_a_url(self):
        server = HTTPServer(("127.0.0.1", 0), DocumentHandler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"

        self.command_line.run(f"{origin}/swagger/v1/swagger.json", "--out", str(self.out))

        self.assertEqual(json.loads((self.out / "http-client.env.json").read_text()), {"dev": {"baseUrl": origin}})

    def test_should_fail_and_write_nothing_when_the_file_is_not_json(self):
        source = self.command_line.document_file("openapi: 3.0.3\n")

        code = self.command_line.run(source, "--out", str(self.out))

        self.assertEqual(
            (code, self.out.exists(), self.command_line.stderr.getvalue()),
            (1, False, f"openapi-to-http: {source} is not JSON (Expecting value at line 1); export a YAML document as JSON\n"),
        )

    def test_should_fail_when_the_file_does_not_exist(self):
        code = self.command_line.run(str(self.command_line.folder / "missing.json"), "--out", str(self.out))

        self.assertEqual((code, self.command_line.stderr.getvalue().startswith("openapi-to-http: ")), (1, True))

    def test_should_fail_when_no_base_url_can_be_found(self):
        source = self.command_line.document_file(json.dumps(a_document({"/orders": {"get": {}}})))

        code = self.command_line.run(source, "--out", str(self.out))

        self.assertEqual(
            (code, self.out.exists(), self.command_line.stderr.getvalue()),
            (1, False, "openapi-to-http: the document names no absolute server URL; pass --base-url\n"),
        )


if __name__ == "__main__":
    unittest.main()
