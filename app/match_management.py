"""Validação do cadastro manual de confrontos entre duas equipes."""
from django import forms
from django.db import transaction
from django.utils import timezone

from .models import (
    Event, Event_sport, Group_phase, Match, Player_match, Player_team_sport,
    Phase, Phase_types, Sexo_types, Team, Team_match, Team_sport, Volley_match,
)


def accessible_events(user):
    events = Event.objects.order_by('name', 'pk')
    if user.is_superuser or user.type == 0:
        return events
    return events.filter(pk=user.event_user_id)


class MatchCreateForm(forms.Form):
    sport = forms.ModelChoiceField(queryset=Event_sport.objects.none(), label='Esporte')
    sexo = forms.TypedChoiceField(choices=Sexo_types.choices, coerce=int, label='Categoria')
    time_a = forms.ModelChoiceField(queryset=Team.objects.none(), label='Time A')
    time_b = forms.ModelChoiceField(queryset=Team.objects.none(), label='Time B')
    datetime = forms.DateTimeField(required=False, label='Data e horário')
    group = forms.ModelChoiceField(queryset=Group_phase.objects.none(), required=False, label='Grupo')
    location = forms.CharField(max_length=100, required=False, label='Local')

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields['sport'].queryset = Event_sport.objects.filter(event=event)
        for name in ('time_a', 'time_b'):
            self.fields[name].queryset = Team.objects.filter(event=event)
        self.fields['group'].queryset = Group_phase.objects.filter(phase__event__event=event)

    def clean(self):
        data = super().clean()
        sport, sexo = data.get('sport'), data.get('sexo')
        a, b = data.get('time_a'), data.get('time_b')
        if a and b and a == b:
            self.add_error('time_b', 'Escolha duas equipes distintas.')
        if sport and sexo is not None:
            if not getattr(sport, {0: 'masc', 1: 'fem', 2: 'mist'}[sexo]):
                self.add_error('sexo', 'Categoria não habilitada nesta modalidade.')
            for field, team in (('time_a', a), ('time_b', b)):
                if team and not Team_sport.objects.filter(
                    event=self.event, sport=sport, sexo=sexo, team=team,
                ).exists():
                    self.add_error(field, 'Equipe não inscrita nesta modalidade e categoria do evento.')
            group = data.get('group')
            if group and (group.phase.event_id != sport.pk or group.phase.sexo != sexo):
                self.add_error('group', 'O grupo deve pertencer à modalidade e categoria selecionadas.')
        scheduled = data.get('datetime')
        if scheduled:
            day = timezone.localtime(scheduled).date() if timezone.is_aware(scheduled) else scheduled.date()
            if ((self.event.date_init and day < self.event.date_init) or
                    (self.event.date_end and day > self.event.date_end)):
                self.add_error('datetime', 'A data deve estar dentro do período do evento.')
        return data

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        # Serializa cadastros do evento nos bancos que suportam bloqueio de linha.
        Event.objects.select_for_update().get(pk=self.event.pk)
        matches = Match.objects.filter(
            event=self.event, sport=data['sport'].sport, sexo=data['sexo'],
            time_match=data['datetime'], group_phase=data['group'],
        ).filter(teams__team=data['time_a']).filter(teams__team=data['time_b'])
        existing = matches.order_by('pk').first()
        if existing:
            return existing, False
        volley = None
        if data['sport'].sport in (1, 2):
            volley = Volley_match.objects.create(event=self.event)
        match = Match.objects.create(
            event=self.event, sport=data['sport'].sport, sexo=data['sexo'],
            time_match=data['datetime'], group_phase=data['group'],
            location=data['location'], volley_match=volley,
        )
        for field in ('time_a', 'time_b'):
            team_match = Team_match.objects.create(match=match, team=data[field])
            players = Player_team_sport.objects.filter(
                team_sport__team=data[field], team_sport__sport=data['sport'],
                team_sport__sexo=data['sexo'], team_sport__event=self.event,
                player__event=self.event,
            ).values_list('player_id', flat=True).distinct()
            for player_id in players:
                Player_match.objects.create(match=match, team_match=team_match, player_id=player_id)
        return match, True


class PhaseCreateForm(forms.Form):
    event_sport = forms.ModelChoiceField(queryset=Event_sport.objects.none(), label='Modalidade')
    name = forms.TypedChoiceField(choices=Phase_types.choices, coerce=int, label='Fase')
    sexo_phase = forms.TypedChoiceField(choices=Sexo_types.choices, coerce=int, label='Categoria')

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_sport'].queryset = Event_sport.objects.filter(event=event)

    def clean(self):
        data = super().clean()
        sport, category = data.get('event_sport'), data.get('sexo_phase')
        if sport and category is not None and not getattr(sport, {0: 'masc', 1: 'fem', 2: 'mist'}[category]):
            self.add_error('sexo_phase', 'Categoria não habilitada nesta modalidade.')
        return data

    def save(self):
        return Phase.objects.get_or_create(event=self.cleaned_data['event_sport'],
                                          name=self.cleaned_data['name'], sexo=self.cleaned_data['sexo_phase'])


class GroupCreateForm(forms.Form):
    phase = forms.ModelChoiceField(queryset=Phase.objects.none(), label='Fase')
    group_name = forms.CharField(max_length=50, label='Nome do grupo')

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phase'].queryset = Phase.objects.filter(event__event=event)

    def save(self):
        return Group_phase.objects.get_or_create(phase=self.cleaned_data['phase'],
                                                 name=self.cleaned_data['group_name'])
