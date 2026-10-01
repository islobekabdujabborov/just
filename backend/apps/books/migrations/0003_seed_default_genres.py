from django.db import migrations


GENRES = [
    ("Roman", "roman"),
    ("Detektiv", "detektiv"),
    ("Fantastika", "fantastika"),
    ("Biznes", "biznes"),
    ("Psixologiya", "psixologiya"),
    ("Tarix", "tarix"),
    ("Ta'lim", "talim"),
    ("Sarguzasht", "sarguzasht"),
    ("She'r", "sher"),
    ("Hikoya", "hikoya"),
]


def seed_genres(apps, schema_editor):
    Genre = apps.get_model("books", "Genre")
    database = schema_editor.connection.alias
    for name, slug in GENRES:
        Genre.objects.using(database).get_or_create(name=name, defaults={"slug": slug})


class Migration(migrations.Migration):
    dependencies = [("books", "0002_initial")]

    operations = [migrations.RunPython(seed_genres, migrations.RunPython.noop)]