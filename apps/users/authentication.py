from rest_framework_simplejwt.authentication import JWTAuthentication


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class to read JWT from 'Authorize' header
    instead of the default 'Authorization'.
    """

    def get_header(self, request):
        header = request.META.get("HTTP_AUTHORIZE")
        return header.encode() if header else None

    def get_raw_token(self, header):
        return header
