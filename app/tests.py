from datetime import date
from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import HttpRequest
from django.test import TestCase, Client
from django.urls import reverse

from .models import Event, Event_sport, Group_phase, Match, Phase, Team, Team_match, Team_sport, Volley_match


class MatchFixtures:
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username='match-admin', password='test')
        cls.event = Event.objects.create(name='Evento A', user=cls.admin, date_init=date(2026, 10, 1), date_end=date(2026, 10, 31))
        cls.other = Event.objects.create(name='Evento B', user=cls.admin)
        cls.sport = Event_sport.objects.create(event=cls.event, sport=0)
        cls.teams = [Team.objects.create(event=cls.event, name=f'Equipe {i}') for i in range(4)]
        for team in cls.teams:
            Team_sport.objects.create(event=cls.event, team=team, sport=cls.sport, sexo=0)
        cls.match = Match.objects.create(event=cls.event, sport=0, sexo=0)
        for team in cls.teams[:2]:
            Team_match.objects.create(match=cls.match, team=team)
        cls.foreign = Match.objects.create(event=cls.other, sport=1)

    def setUp(self):
        self.login(self.admin)
        self.url = reverse('games')

    def login(self, user):
        self.client = Client()
        with patch.object(HttpRequest, "user_agent", Mock(device=Mock(family="PC"), browser=Mock(family="Test"), os=Mock(family="Linux")), create=True):
            self.client.force_login(user)

    def payload(self, **changes):
        data = dict(create_match='1', sport=self.sport.pk, sexo=0,
                    time_a=self.teams[0].pk, time_b=self.teams[1].pk,
                    datetime='2026-10-10T10:00', location='Quadra A')
        data.update(changes)
        return data

    def post(self, **changes):
        return self.client.post(f'{self.url}?e={self.event.pk}', self.payload(**changes))


class MatchManagementTests(MatchFixtures, TestCase):
    def test_explicit_event_selection_and_isolation(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Selecione um evento para visualizar')
        self.assertEqual(response.context['context'], [])
        response = self.client.get(self.url, {'e': self.event.pk})
        self.assertEqual([i['match'].pk for i in response.context['context']], [self.match.pk])
        session = self.client.session
        session['selected_event_id'] = str(self.event.pk)
        session.save()
        for params in ({}, {'e': ''}):
            self.assertEqual(self.client.get(self.url, params).context['context'], [])

    def test_combined_filters_including_zero_values(self):
        params = dict(e=self.event.pk, sport='0', genre='0', team=self.teams[0].pk, q='Equipe 0')
        response = self.client.get(self.url, params)
        self.assertEqual(len(response.context['context']), 1)
        for key, value in [('genre', '1'), ('q', 'inexistente'), ('team', self.teams[3].pk), ('sport', 'invalid')]:
            with self.subTest(key=key):
                self.assertEqual(self.client.get(self.url, {**params, key: value}).context['context'], [])

    def test_invalid_event(self):
        self.assertEqual(self.client.get(self.url, {'e': 'abc'}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'e': '999999'}).status_code, 404)

    def test_create_and_resubmission_preserve_two_teams(self):
        self.assertEqual(self.post().status_code, 302)
        self.assertEqual(self.post(time_a=self.teams[1].pk, time_b=self.teams[0].pk).status_code, 302)
        created = Match.objects.filter(event=self.event).exclude(pk=self.match.pk)
        self.assertEqual(created.count(), 1)
        self.assertEqual(created.get().teams.count(), 2)

    def test_different_confrontations_at_same_time(self):
        self.post()
        self.post(time_a=self.teams[2].pk, time_b=self.teams[3].pk)
        self.assertEqual(Match.objects.filter(event=self.event).count(), 3)

    def test_invalid_registration_does_not_write(self):
        foreign_team = Team.objects.create(event=self.other, name='Outro')
        group = Group_phase.objects.create(phase=Phase.objects.create(event=self.sport, sexo=1))
        for changes in [dict(time_b=self.teams[0].pk), dict(time_b=foreign_team.pk),
                        dict(sexo=1), dict(group=group.pk), dict(datetime='bad'),
                        dict(datetime='2026-11-01T12:00'), dict(sport='bad'), dict(time_b='')]:
            with self.subTest(changes=changes):
                self.assertEqual(self.post(**changes).status_code, 400)
                self.assertEqual(Match.objects.count(), 2)

    def test_optional_schedule(self):
        self.assertEqual(self.post(datetime='', time_b=self.teams[2].pk).status_code, 302)

    def test_volleyball_duplicate_and_atomic_rollback(self):
        self.sport.sport = 1
        self.sport.save()
        self.post()
        self.post()
        self.assertEqual(Volley_match.objects.count(), 1)
        count = Match.objects.count()
        with patch('app.match_management.Team_match.objects.create', side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):
                self.post(time_b=self.teams[2].pk)
        self.assertEqual(Match.objects.count(), count)
        self.assertEqual(Volley_match.objects.count(), 1)

    def test_permission_and_event_scope(self):
        user = get_user_model().objects.create_user(username='viewer', type=3, event_user=self.event)
        user.groups.clear()
        user.user_permissions.add(Permission.objects.get(codename='view_match'))
        self.login(user)
        user.groups.clear()
        self.assertEqual(self.client.get(self.url).context['context'], [])
        self.assertEqual(self.client.get(self.url, {'e': self.other.pk}).status_code, 404)
        # O handler403 existente redireciona para o painel.
        self.assertRedirects(self.post(), reverse('Home'), fetch_redirect_response=False)
        self.assertEqual(Match.objects.count(), 2)
        foreign_sport = Event_sport.objects.create(event=self.other, sport=0)
        for name in ('get_teams', 'get_groups', 'get_sexos'):
            self.assertEqual(self.client.get(reverse(name), {'sport': foreign_sport.pk}).status_code, 404)

    def test_create_requires_selected_event(self):
        self.client.post(self.url, self.payload())
        self.assertEqual(Match.objects.count(), 2)
