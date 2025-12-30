# core/exception_handler.py
from __future__ import annotations

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import ApiError


def _first_validation_detail(exc: ValidationError) -> dict:
    """
    Приводим DRF ValidationError к формату ТЗ:
    details: { field: "...", message: "..." }
    """
    detail = exc.detail

    # detail может быть list/ dict
    if isinstance(detail, list) and detail:
        return {"field": "non_field_errors", "message": str(detail[0])}

    if isinstance(detail, dict) and detail:
        field = next(iter(detail.keys()))
        msg = detail[field]
        if isinstance(msg, list) and msg:
            msg = msg[0]
        return {"field": str(field), "message": str(msg)}

    return {"field": "unknown", "message": "Некорректные данные"}


def custom_exception_handler(exc, context):
    # 1) Наши доменные ошибки (по ТЗ)
    if isinstance(exc, ApiError):
        return Response({"success": False, "error": exc.to_payload()}, status=exc.status_code)

    # 2) 404
    if isinstance(exc, (Http404, NotFound)):
        return Response(
            {"success": False, "error": {"code": "NOT_FOUND", "message": "Ресурс не найден"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 3) Ошибки валидации DRF
    if isinstance(exc, ValidationError):
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Ошибка валидации данных",
                    "details": _first_validation_detail(exc),
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4) Остальные DRF APIExceptions (403/401 и т.п.) — отдаём в формате ТЗ
    if isinstance(exc, APIException):
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(getattr(exc, "detail", "Ошибка запроса")),
                },
            },
            status=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        )

    # 5) Фолбек на стандартный обработчик
    resp = drf_exception_handler(exc, context)
    if resp is not None:
        return Response(
            {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"}},
            status=resp.status_code,
        )

    # 6) Неожиданные ошибки
    return Response(
        {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )