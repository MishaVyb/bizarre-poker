import os

import pydantic
from core.utils import StrColors, init_logger
from django.core.management.base import BaseCommand
from django.db import models
from games.models import Game, Player
from games.services import actions, stages
from games.services.processors import AutoProcessor, BaseProcessor
from users.models import User

logger = init_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE_PATH = os.path.join(CURRENT_DIR, 'data.json')


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
        parser.add_argument(
            'file_path',
            type=str,
            nargs='?',
            default=DEFAULT_FILE_PATH,
        )

    def handle(self, *args, **options):
        message = (
            '\n'
            'This command will {erase} all current data, '
            'are you sure? Y/n '.format(erase=StrColors.red('erase'))
        )
        if input(message) != 'Y':
            self.stdout.write(StrColors.bold('adopted.'))
            return

        data = TestDataSchema.parse_file(options['file_path'])
        for model in [User, Player, Game]:
            model.objects.all().delete()

        for user_data in data.users:
            user = User(**user_data)
            password = user_data.get('password') or user.username
            user.set_password(password)

            # Profile objects creates inside at clean(..) method
            user.save()
            admin = 'admin' if user.is_staff else ''
            logger.info(
                f'User {admin} created. Authentication credentials: '
                f'login "{user.username}" password "{password}"'
            )

        for game_data in data.games:
            players_order_cases = [
                models.When(username=player, then=models.Value(idx))
                for idx, player in enumerate(game_data.players)
            ]
            users = (
                User.objects.filter(username__in=game_data.players)
                .annotate(ordering=models.Case(*players_order_cases))
                .order_by('ordering')
            )

            game = Game(players=users, pk=game_data.pk, commit=True)
            logger.info(f'Game created. Players: {game.players}')

            if game_data.run:
                kwargs = {
                    k: getattr(stages, v, None) or getattr(actions, v)
                    for k, v in game_data.run.items()
                }
                AutoProcessor(game, **kwargs, autosave=False).run()
                BaseProcessor(game).run()

        self.stdout.write(StrColors.bold('\nSuccess! ') + 'All test data applyed. ')
