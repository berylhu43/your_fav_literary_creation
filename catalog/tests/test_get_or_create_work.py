import pytest

from catalog import services
from catalog.models import Catalog


def _fake_movie_fields():
    return {"title": "Inception", "genre_names": ["Science Fiction", "Action"]}


def _fake_tv_fields():
    return {"title": "Severance", "genre_names": ["Drama"], "created_by": []}


@pytest.fixture
def stub_external(monkeypatch):
    """
    no internet access, so we stub out the external API calls to return fake data
    """
    monkeypatch.setattr(services, "_map_movie", lambda ext_id: _fake_movie_fields())
    monkeypatch.setattr(services, "_map_tv", lambda ext_id: _fake_tv_fields())
    monkeypatch.setattr(services, "_add_movie_credits", lambda work, ext_id: None)
    monkeypatch.setattr(
        services, "_add_tv_credits", lambda work, ext_id, created_by: None
    )


@pytest.mark.django_db
def test_reuses_existing_row(stub_external):
    """
    test that get_or_create_work reuses an existing row if it exists
    """
    first = services.get_or_create_work(
        media_type=Catalog.MediaType.MOVIE, external_id=27205
    )
    second = services.get_or_create_work(
        media_type=Catalog.MediaType.MOVIE, external_id=27205
    )
    assert first.pk == second.pk
    assert Catalog.objects.count() == 1


@pytest.mark.django_db
def test_movie_and_tv_same_id_do_not_collide(stub_external):
    """
    movie and tv type with the same external_id should not collide
    """
    movie = services.get_or_create_work(
        media_type=Catalog.MediaType.MOVIE, external_id=27205
    )
    tv = services.get_or_create_work(media_type=Catalog.MediaType.TV, external_id=27205)
    assert movie.pk != tv.pk
    assert Catalog.objects.count() == 2
    assert movie.media_type == Catalog.MediaType.MOVIE
    assert tv.media_type == Catalog.MediaType.TV


@pytest.mark.django_db
def test_external_id_int_and_str_dedup(stub_external):
    """
    Test the conversion of external_id from int to str,
    ensuring that the same work is not duplicated in the database.
    """
    a = services.get_or_create_work(
        media_type=Catalog.MediaType.MOVIE, external_id=27205
    )
    b = services.get_or_create_work(
        media_type=Catalog.MediaType.MOVIE, external_id="27205"
    )
    assert a.pk == b.pk
    assert Catalog.objects.count() == 1


@pytest.mark.django_db
def test_returns_none_when_mapper_fails(monkeypatch):
    """
    when _map_* return None, get_or_create_work should return None and not create a row
    """
    monkeypatch.setattr(services, "_map_movie", lambda ext_id: None)
    result = services.get_or_create_work(
        media_type=Catalog.MediaType.MOVIE, external_id=999999
    )
    assert result is None
    assert Catalog.objects.count() == 0


def test_unknown_media_type_returns_none():
    """
    returns None if media_type is not recognized
    """
    assert services.get_or_create_work(media_type="podcast", external_id=1) is None
