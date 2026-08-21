from rest_framework.renderers import JSONRenderer


class ApiJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None

        if response and 200 <= response.status_code < 300:
            formatted_data = {
                "success": True,
                "data": data,
                "error": None
            }
            return super().render(formatted_data, accepted_media_type, renderer_context)
        return super().render(data, accepted_media_type, renderer_context)
