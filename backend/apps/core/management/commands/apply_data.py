import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
import pydantic
from core.functools.utils import init_logger
from core.functools.utils import StrColors

from games.models import Game, Player
from games.services import actions, stages
from users.models import Profile, User
from games.services.processors import AutoProcessor

logger = init_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILE_PATH = os.path.join(CURRENT_DIR, 'data.json')

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
            default=TEST_FILE_PATH,
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
            logger.info(
                f'User created. Authentication credentials: '
                f'login "{user.username}" password "{password}"'
            )

        for game_data in data.games:
            game = Game(
                players=User.objects.filter(username__in=game_data.players),
                pk=game_data.pk,
                commit=True,
            )
            logger.info(f'Game created. Players: {game.players}')

            if game_data.run:
                kwargs = {
                    k: getattr(stages, v, None) or getattr(actions, v)
                    for k, v in game_data.run.items()
                }
                AutoProcessor(game, **kwargs).run()

        self.stdout.write(StrColors.bold('\nSuccess! ') + 'All test data applyed. ')
