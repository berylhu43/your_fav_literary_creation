from .models import Catalog

def get_or_create_work(*, media_type, title, source=Catalog.Source.MANUAL):
    work, created = Catalog.objects.get_or_create(
        media_type = media_type,
        title = title, 
        defaults={
            'source': source,
        },
    )
    return work