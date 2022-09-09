"""
Main config file for pytest.
There are applying all custom fixtures as pytest plugins.
"""


pytest_plugins = [
    'tests.fixtures.fixture_users',
    'tests.fixtures.fixture_games',
    'tests.fixtures.fixture_decks',
    'tests.fixtures.fixture_setup_classes',
]
