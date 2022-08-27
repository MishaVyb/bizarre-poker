from copy import deepcopy
import logging
from pprint import pformat
from typing import Any, Iterable, Optional
from django.db import models
from core.functools.utils import StrColors, init_logger
logger = init_logger(__name__, logging.INFO)


class FullCleanSavingMixin():
    def clean(self):
        raise NotImplementedError

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
    ) -> None:
        # pk is None for first game saving (just after creation)
        # so validation won't work because of failing ralated ForigenKey fields
        # we need to call save before to define pk and
        if not self.pk:
            super().save(force_insert, force_update, using, update_fields)
            self.full_clean()
        else:
            self.full_clean()
            super().save(force_insert, force_update, using, update_fields)



class CreatedModifiedModel(models.Model):
    """Abstract model with auto filled created and modified date.

    Ordering by creation date ascending.
    """

    created = models.DateTimeField('creation data', auto_now_add=True, db_index=True)
    modified = models.DateTimeField('modification data', auto_now=True, db_index=True)
    """Automatically set the field to now every time the object is saved by calling
    save() method. Notice, that it is not getting affect by calling update() method.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._db_data = self.get_current_fields()

    def update(self, **kwargs):
        for attr, value in kwargs.items():
            assert hasattr(self, attr)
            setattr(self, attr, value)
            self.save()

    def get_current_fields(self) -> dict[str, Any]:
        return {f.attname: deepcopy(getattr(self, f.attname)) for f in self._meta.fields}

    def get_changed_fields(self) -> dict[str, Any]:
        # db_data = self.__class__.objects.get(pk=self.pk).get_current_fields()
        current_data = self.get_current_fields()
        return {k: v for k, v in current_data.items() if v != self._db_data[k]}

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
    ) -> None:
        if self.pk:
            changed = self.get_changed_fields()
            for k, v in changed.items():
                if isinstance(v, list) and len(v) > 5:
                    changed[k] = str(v[:4]) + '...'
            logger.info(f'{StrColors.green("Saving")} {self}... Changed fields: {changed}')
        else:
            logger.info(f'{StrColors.warning("Creation")} {self}')


        # pk is None for first game saving (just after creation)
        # so validation won't work because of failing ralated ForigenKey fields
        # we need to call save before to define pk and
        if not self.pk:
            super().save(force_insert, force_update, using, update_fields)
            self.full_clean()
        else:
            self.full_clean()
            super().save(force_insert, force_update, using, update_fields)

        self._db_data = self.get_current_fields()


    class Meta:
        abstract = True

        # WARNING!
        # do not use descending ordering, it takes PyTest falling
        # and breks down others not obvious dependencies
        ordering = ['created']
