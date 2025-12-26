from drf_yasg.inspectors import SwaggerAutoSchema

class CustomAutoSchema(SwaggerAutoSchema):
    def get_tags(self):
        tags = super().get_tags()
        hidden_tags = {'appointments', 'commerce', 'events', 'topics'}
        return [tag for tag in tags if tag not in hidden_tags]