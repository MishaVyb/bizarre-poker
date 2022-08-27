"""
Main config file for pytest.
There are applying all custom fixtures as pytest plugins.
"""


pytest_plugins = [
    'api.tests.fixtures.game_data',
]
