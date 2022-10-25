from copy import deepcopy
import functools
from typing import Any, Callable, Iterable, Iterator, Optional, TypeAlias, TypeVar
import typing
from django.db import models
from core.utils import StrColors, init_logger

logger = init_logger(__name__)


if typing.TYPE_CHECKING:
    _TYPE_MODEL: TypeAlias = models.Model
else:
    _TYPE_MODEL = object


_T = TypeVar('_T')


def get_list_default():
    return []


def related_manager_method(wrapped: Callable):
    @functools.wraps(wrapped)
    def wrapper(self: models.Manager, *args, **kwargs):
        assert isinstance(self, models.Manager), 'decorator is only for Manager methods'
        if hasattr(self, 'instance'):
            return wrapped(self, *args, **kwargs)
        raise AttributeError(
            f'{wrapped.__name__} is forbidden to use via class manager. '
        )

    return wrapper


class IterableManager(models.Manager[_T]):
    def __iter__(self) -> Iterator[_T]:
        return iter(self.all())

    def __getitem__(self, index: int):
        return self.all()[index]

    def __bool__(self):
        return self.exists()

    def __len__(self):
        return self.count()

    def __str__(self) -> str:
        return '[' + ' '.join(str(b) for b in self.all()) + ']'


class UpdateMethodMixin:
    def update(self, **kwargs):
        for attr, value in kwargs.items():
            assert hasattr(self, attr)
            setattr(self, attr, value)
            self.save()


class ChangedFieldsLoggingMixin(_TYPE_MODEL):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._db_data = self.get_current_fields()

    def get_current_fields(self) -> dict[str, Any]:
        return {
            f.attname: deepcopy(getattr(self, f.attname)) for f in self._meta.fields
        }

    def get_changed_fields(self) -> dict[str, Any]:
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
            logger.debug(
                f'{StrColors.green("Saving")} {self}... Changed fields: {changed}'
            )
        else:
            logger.debug(f'{StrColors.yellow("Creation")} {self}')

        super().save(force_insert, force_update, using, update_fields)
        self._db_data = self.get_current_fields()

    class Meta:
        abstract = True

class CleanManagerMixin():

    def bulk_create(self, *args, **kwargs):
        raise RuntimeError(
            'If FullCleanSavingMixin are used, it depricates create objects by '
            '`bulk_create` method. Because in that way cleans methods won`t call. '
        )


class FullCleanSavingMixin(_TYPE_MODEL):
    _presave_flag = False


    def presave(self):
        """
        Set pre-save flag True.

        Not calling for real save. Do it yourself later, before ending cureent request
        handling.
        """
        self._presave_flag = True

    def init_clean(self):
        """
        Called before first objects saving (when pk is None).
        """
        pass

    def post_init_clean(self):
        """
        Called after first objects saving. When pk has defined and model instance could
        be use in related relationships.
        """
        pass

    def clean(self):
        """
        Called every time before model saving, exept first time savings.
        """
        pass

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
        *,
        only_if_presave: bool = False,
    ) -> None:
        if only_if_presave:
            if not self._presave_flag:
                return

        if not self.pk:
            self.init_clean()
            super().save(force_insert, force_update, using, update_fields)
            self.post_init_clean()
        else:
            self.full_clean()
            super().save(force_insert, force_update, using, update_fields)


class ExtendedSavingMixin(FullCleanSavingMixin, ChangedFieldsLoggingMixin):
    # not implemented yet
    pass


class CreatedModifiedModel(models.Model):
    """
    Abstract model with auto filled created and modified date.

    Ordering by creation date ascending.
    """

    created = models.DateTimeField('creation data', auto_now_add=True, db_index=True)
    modified = models.DateTimeField('modification data', auto_now=True, db_index=True)
    """
    Automatically set the field to now every time the object is saved by calling
    save() method. Notice, that it is not getting affect by calling update() method.
    """

    class Meta:
        abstract = True
        ordering = ['created']
