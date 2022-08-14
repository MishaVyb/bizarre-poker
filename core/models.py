from django.db import models


class CreatedModifiedModel(models.Model):
    """Abstract model with auto filled created and modified date.

    Ordering by creation date ascending.
    """

    created = models.DateTimeField('creation data', auto_now_add=True, db_index=True)
    modified = models.DateTimeField('modification data', auto_now=True, db_index=True)
    """Automatically set the field to now every time the object is saved by calling
    save() method. Notice, that it is not getting affect by calling update() method.
    """

    def update(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)
            self.save()

    class Meta:
        abstract = True

        # WARNING!
        # do not use descending ordering, it takes PyTest falling
        # and breks down others not obvious dependencies
        ordering = ['created']
