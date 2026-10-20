from django.db import transaction


def collect_model_files(queryset, field_names):
    collected = []
    for instance in queryset.only("pk", *field_names).iterator():
        for field_name in field_names:
            file_field = getattr(instance, field_name)
            if file_field and file_field.name:
                collected.append((file_field.storage, file_field.name))
    return collected


def schedule_file_cleanup(files):
    unique_files = {(id(storage), name): (storage, name) for storage, name in files}
    for storage, name in unique_files.values():
        transaction.on_commit(
            lambda storage=storage, name=name: storage.delete(name),
            robust=True,
        )
