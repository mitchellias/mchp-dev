from django.template import Library, Node, TemplateSyntaxError, Variable

from dashboard.utils import WEATHER_ICONS

register = Library()

class WeatherNode(Node):
    def __init__(self, icon, text):
        self.icon = Variable(icon)
        self.text = Variable(text)

    def render(self, context):
        icon = int(self.icon.resolve(context))
        text = self.text.resolve(context)

        tooltip = 'data-toggle="tooltip" data-original-title="{}"'.format(text)
        if icon in WEATHER_ICONS:
            weather = WEATHER_ICONS[icon]
            text = ''
        else:
            weather = 'wi wi-alien'
            text = ' ayy lmao'
        return '<i {} class="{}">{}</i>'.format(tooltip, weather, text)

@register.tag
def weather_icon(parser, token):
    try:
        tag_name, weather_icon, weather_text = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError("weather tag requires a single icon argument")
    return WeatherNode(weather_icon, weather_text)
