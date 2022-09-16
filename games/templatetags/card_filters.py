from django import template
from django.contrib.auth import get_user_model

from core.functools.decorators import temporally
from games.services.cards import Card, CardList

register = template.Library()
User = get_user_model()


@register.filter
@temporally(Card.Text, str_method='emoji_shirt')
def hiden(cards: CardList) -> str:
    return str(cards)
