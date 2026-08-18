from django.db import models

# Create your models here.
class Catalog(models.Model):
    class MediaType(models.TextChoices):
        MOVIE = 'movie', 'Movie'
        TV = 'tv', 'TV Show'
        BOOK = 'book', 'Book'

    class Source(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        TMDB = 'tmdb', 'TMDB'
        GOOGLE_BOOKS = 'googlebooks', 'Google Books'

    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    title = models.CharField(max_length=255)
    creator = models.CharField(max_length=255, blank=True)
    genres = models.ManyToManyField('Genre', blank=True, related_name='catalogs')
    release_year = models.PositiveIntegerField(null=True, blank=True)

    pages = models.PositiveIntegerField(null=True, blank=True)
    runtime = models.PositiveIntegerField(null=True, blank=True)
    episodes = models.PositiveIntegerField(null=True, blank=True)

    cover_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )

    external_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} ({self.get_media_type_display()})'



class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Artist(models.Model):
    name = models.CharField(max_length=100)
    external_id = models.CharField(max_length=100, blank=True)
    source = models.CharField(
        max_length=20,
        choices=Catalog.Source.choices,
        blank=True,
    )

    def __str__(self):
        return self.name


class Credit(models.Model):
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name='credits')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='credits')
    role = models.CharField(max_length=50)

    def __str__(self):
        return f'{self.artist.name} as {self.role} in {self.catalog.title}'

    