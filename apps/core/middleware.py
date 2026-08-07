import logging
import time

logger = logging.getLogger("awaaz.requests")


class RequestLoggingMiddleware:
    """Logs method, path, status, and elapsed time for every API request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        elapsed = (time.monotonic() - start) * 1000

        if request.path.startswith("/api/"):
            user = getattr(request, "user", None)
            uid = user.id if user and user.is_authenticated else "anon"
            logger.info(
                "%s %s → %s (%.1fms) user=%s",
                request.method,
                request.path,
                response.status_code,
                elapsed,
                uid,
            )

        return response
