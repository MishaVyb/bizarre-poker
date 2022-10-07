import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
import pydantic
from core.functools.utils import StrColors

from games.models import Game, Player
from games.services import actions, stages
from users.models import Profile, User
from games.services.processors import AutoProcessor


class GameSchema(pydantic.BaseModel):
    pk: int
    players: list[str]
    run: dict[str, str] = {}


class TestDataSchema(pydantic.BaseModel):
    users: list[dict[str, str]]
    games: list[GameSchema]


class Command(BaseCommand):
    help = 'Erasing full data on db and then loading test data to it. '
    requires_migrations_checks = True

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)

    def handle(self, *args, **options):
        self.stdout.write(
            '\n'
            'This command will {erase} all current data, '
            'are you sure? Y/n'.format(erase=StrColors.red('erase'))
        )
        if input() != 'Y':
            self.stdout.write(StrColors.bold('adopted.'))
            return

        data = TestDataSchema.parse_file(options['file_path'])
        for model in [User, Player, Game]:
            model.objects.all().delete()

        users = User.objects.bulk_create([User(**user) for user in data.users])
        Profile.objects.bulk_create([Profile(user=user) for user in users])

        for game_data in data.games:
            game = Game(
                players=User.objects.filter(username__in=game_data.players),
                pk=game_data.pk,
                commit=True,
            )
            if game_data.run:
                kwargs = {
                    k: getattr(stages, v, None) or getattr(actions, v)
                    for k, v in game_data.run.items()
                }
                AutoProcessor(game, **kwargs).run()

        self.stdout.write(StrColors.bold('\nSuccess! ') + 'All test data applyed. ')
