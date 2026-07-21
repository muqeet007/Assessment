import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.routing_service import RoutingService


def health_check(request):
    return JsonResponse({"status": "ok", "message": "Fuel optimizer routing app is ready."})


@csrf_exempt
@require_POST
def route(request):
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"errors": {"detail": ["Invalid JSON body."]}}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"errors": {"detail": ["Request body must be a JSON object."]}}, status=400)

    errors = {}

    start = data.get("start")
    if start is None or (isinstance(start, str) and not start.strip()):
        errors["start"] = ["This field is required."]
    elif not isinstance(start, str):
        errors["start"] = ["This field must be a string."]

    destination = data.get("destination")
    if destination is None or (isinstance(destination, str) and not destination.strip()):
        errors["destination"] = ["This field is required."]
    elif not isinstance(destination, str):
        errors["destination"] = ["This field must be a string."]

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    routing_service = RoutingService()
    route_result = routing_service.get_route(start, destination)

    return JsonResponse(route_result, status=200)
