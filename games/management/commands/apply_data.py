import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
import pydantic
from core.functools.utils import StrColors

from games.models import Game, Player
from users.models import User
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
            'This command will {erase} all current data, '
            'are you sure? Y/n'.format(erase=StrColors.red('erase'))
        )
        if input() != 'Y':
            self.stdout.write(StrColors.bold('adopted.'))
            return

        data = TestDataSchema.parse_file(options['file_path'])
        for model in [User, Player, Game]:
            model.objects.all().delete()
        User.objects.bulk_create([User(**user) for user in data.users])
        for game_data in data.games:
            game = Game(
                players=User.objects.filter(username__in=game_data.players),
                commit=True,
            )
            if game_data.run:
                AutoProcessor(game, **game_data.run).run()

        self.stdout.write(StrColors.green('success!'))
