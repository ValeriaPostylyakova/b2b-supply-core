import re

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class PDFGenerationRateThrottle(UserRateThrottle):
    scope = "pdf_generation"


class ExcelUploadRateThrottle(UserRateThrottle):
    scope = "excel_upload"


class FlexibleRateThrottle(SimpleRateThrottle):
    lookup_fields = []

    def parse_rate(self, rate):
        if rate is None:
            return (None, None)

        match = re.match(r"^(\d+)/(\d*)([smhd])$", rate)
        if not match:
            raise ValueError(f"Некорректный формат THROTTLE_RATE: '{rate}'")

        num_requests = int(match.group(1))
        period_value = int(match.group(2)) if match.group(2) else 1
        period_type = match.group(3)

        duration_multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        duration = period_value * duration_multipliers[period_type]

        return (num_requests, duration)

    def get_cache_key(self, request, view):
        identifier = None

        for field in self.lookup_fields:
            identifier = request.data.get(field)
            if identifier:
                break

        if not identifier:
            identifier = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": identifier}


class OTPRequestRateThrottle(FlexibleRateThrottle):
    scope = "otp_request"
    lookup_fields = ["email"]


class OTPVerifyRateThrottle(FlexibleRateThrottle):
    scope = "otp_verify"
    lookup_fields = ["email"]


class LoginRateThrottle(FlexibleRateThrottle):
    scope = "login"
    lookup_fields = ["email"]
