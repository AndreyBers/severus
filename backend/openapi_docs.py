from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        error_schema = {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {
                    "type": "object",
                    "required": [
                        "code", "message", "field", "retryable"
                    ],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "field": {
                            "type": ["string", "null"]
                        },
                        "retryable": {"type": "boolean"},
                    },
                }
            },
        }

        schema.setdefault("components", {}).setdefault(
            "schemas", {}
        )["ApiErrorResponse"] = error_schema

        for path in schema.get("paths", {}).values():
            for operation in path.values():
                if not isinstance(operation, dict):
                    continue

                response = operation.get(
                    "responses", {}
                ).get("422")

                if response is not None:
                    response["description"] = (
                        "Некорректные параметры запроса"
                    )
                    response["content"] = {
                        "application/json": {
                            "schema": {
                                "$ref": (
                                    "#/components/schemas/"
                                    "ApiErrorResponse"
                                )
                            }
                        }
                    }

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
