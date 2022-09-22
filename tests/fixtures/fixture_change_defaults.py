import pytest
from games.services.stages import StagesContainer


@pytest.fixture
def disable_save_after_process_stoped():
    StagesContainer._save_after_proces_stoped = False
    yield
    StagesContainer._save_after_proces_stoped = True
