
from django import template, forms
from games import models
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser

from core.functools.decorators import temporary_globals
from games.backends.cards import Card, CardList
from games.backends.cards import CardList


register = template.Library()
#User = get_user_model()



@register.filter
@temporary_globals(
        Card__STR_METHOD=Card.Text.emoji_shirt,
        JokerCard__STR_METHOD=Card.Text.emoji_shirt,
    )
def hiden(cards: CardList) -> str:
    return str(cards)