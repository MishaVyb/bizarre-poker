




from django import forms
from games.models import PlayerBet


class PlayerBetForm(forms.ModelForm):
    class Meta:
        model = PlayerBet
        fields = ('value',)
