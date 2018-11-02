from django.utils.text import slugify

def slugify_underscore(text):
    return slugify(text).replace('-', '_')