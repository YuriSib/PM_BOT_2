from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = []

    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'p', 'li'):
            self.data.append('\n')

    def handle_data(self, d):
        self.data.append(d)

    def get_data(self):
        return ''.join(self.data).strip()


def strip_tags(html):
    stripper = HTMLStripper()
    stripper.feed(html)
    return stripper.get_data()