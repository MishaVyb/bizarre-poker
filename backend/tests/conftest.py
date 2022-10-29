"""Main config file for pytest.

Here are applying all custom fixtures as pytest plugins.
"""


import os


pytest_plugins = [
    'tests.fixtures.fixture_users',
    'tests.fixtures.fixture_games',
    'tests.fixtures.fixture_decks',
    'tests.fixtures.fixture_setup_classes',
    'tests.fixtures.fixture_combos',
    'tests.fixtures.fixture_data',
]


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ISSUES_PATH = os.path.join(CURRENT_DIR, 'issues')