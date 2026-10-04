from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from .match_management import MatchCreateForm, accessible_events
from .middleware import EventFilterPersistenceMiddleware
from .models import (Event_sport, Group_phase, Match, Phase, Player, Player_match,
                     Player_team_sport, Point, Team_match, Team_sport, Volley_match)
from .tests import MatchFixtures


class EventSelectionUnitTests(SimpleTestCase):
    def request(self, path, params=None):
        request = RequestFactory().get(path, params or {})
        request.user = SimpleNamespace(is_authenticated=True, is_staff=True, type=0)
        request.session = {'selected_event_id': '9'}
        return request

    def test_match_pages_ignore_saved_event(self):
        for name in ('games', 'matches_manage'):
            with self.subTest(page=name):
                request = self.request(reverse(name))
                EventFilterPersistenceMiddleware(lambda r: HttpResponse())(request)
                self.assertNotIn('e', request.GET)

    def test_other_pages_still_restore_saved_event(self):
        request = self.request(reverse('team_manage'))
        EventFilterPersistenceMiddleware(lambda r: HttpResponse())(request)
        self.assertEqual(request.GET['e'], '9')

    def test_other_pages_still_remember_explicit_event(self):
        request = self.request(reverse('team_manage'), {'e': '12'})
        EventFilterPersistenceMiddleware(lambda r: HttpResponse())(request)
        self.assertEqual(request.session['selected_event_id'], '12')


class MatchFormTests(MatchFixtures, TestCase):
    def form(self, **changes):
        return MatchCreateForm(self.payload(**changes), event=self.event)

    def test_accessible_events_for_admin_and_regular_user(self):
        self.assertEqual(set(accessible_events(self.admin)), {self.event, self.other})
        user = SimpleNamespace(is_superuser=False, type=3, event_user_id=self.event.pk)
        self.assertEqual(list(accessible_events(user)), [self.event])
        user.event_user_id = None
        self.assertFalse(accessible_events(user).exists())

    def test_disabled_category_rejected_even_with_registered_teams(self):
        self.sport.masc = False
        self.sport.save()
        form = self.form()
        self.assertFalse(form.is_valid())
        self.assertIn('sexo', form.errors)

    def test_foreign_sport_and_group_rejected(self):
        sport = Event_sport.objects.create(event=self.other, sport=0)
        group = Group_phase.objects.create(phase=Phase.objects.create(event=sport, sexo=0))
        for changes, field in (({'sport': sport.pk}, 'sport'), ({'group': group.pk}, 'group')):
            with self.subTest(field=field):
                form = self.form(**changes)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_group_must_match_exact_modality_and_category(self):
        another = Event_sport.objects.create(event=self.event, sport=1)
        for sport, sexo in ((another, 0), (self.sport, 1)):
            group = Group_phase.objects.create(phase=Phase.objects.create(event=sport, sexo=sexo))
            form = self.form(group=group.pk)
            self.assertFalse(form.is_valid())
            self.assertIn('group', form.errors)

    def test_valid_group_and_optional_fields(self):
        group = Group_phase.objects.create(phase=Phase.objects.create(event=self.sport, sexo=0))
        form = self.form(group=group.pk, datetime='', location='')
        self.assertTrue(form.is_valid(), form.errors)
        match, created = form.save()
        self.assertTrue(created)
        self.assertEqual(match.group_phase, group)
        self.assertIsNone(match.time_match)
        self.assertEqual(match.status, 0)

    def test_event_date_boundaries(self):
        for value, valid in [('2026-09-30T12:00', False), ('2026-10-01T12:00', True),
                             ('2026-10-31T12:00', True), ('2026-11-01T12:00', False)]:
            with self.subTest(value=value):
                self.assertEqual(self.form(datetime=value).is_valid(), valid)

    def test_event_without_dates_allows_schedule(self):
        self.event.date_init = self.event.date_end = None
        self.assertTrue(self.form(datetime='2027-01-01T12:00').is_valid())

    def test_location_length_and_required_fields(self):
        for field in ('sport', 'sexo', 'time_a', 'time_b'):
            with self.subTest(field=field):
                form = self.form(**{field: ''})
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
        self.assertFalse(self.form(location='a' * 101).is_valid())

    def test_roster_copied_and_resubmission_does_not_replace_it(self):
        player = Player.objects.create(name='Atleta fictício', admin=self.admin, event=self.event)
        registration = Player_team_sport.objects.create(player=player, team_sport=Team_sport.objects.get(team=self.teams[0]))
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        match, _ = form.save()
        self.assertEqual(list(Player_match.objects.filter(match=match).values_list('player_id', flat=True)), [player.pk])
        registration.delete()
        _, created = form.save()
        self.assertFalse(created)
        self.assertEqual(Player_match.objects.filter(match=match).count(), 1)

    def test_sitting_volleyball_gets_set_control(self):
        self.sport.sport = 2
        self.sport.save()
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        match, _ = form.save()
        self.assertIsNotNone(match.volley_match_id)
        self.assertEqual(match.volley_match.event, self.event)


class MatchRegressionTests(MatchFixtures, TestCase):
    def restricted_user(self, *permissions):
        user = get_user_model().objects.create_user(username='restricted', type=3, event_user=self.event)
        self.login(user)
        user.groups.clear()
        user.user_permissions.add(*Permission.objects.filter(codename__in=permissions))
        return user

    def test_legacy_list_redirect_preserves_filters(self):
        response = self.client.get(reverse('matches_manage'), {'e': self.event.pk, 'sport': 0})
        self.assertRedirects(response, f'{self.url}?e={self.event.pk}&sport=0', fetch_redirect_response=False)

    def test_lookup_options_are_event_and_category_scoped(self):
        male = Group_phase.objects.create(phase=Phase.objects.create(event=self.sport, sexo=0))
        Group_phase.objects.create(phase=Phase.objects.create(event=self.sport, sexo=1))
        response = self.client.get(reverse('get_groups'), {'sport': self.sport.pk, 'sexo': 0})
        self.assertEqual([g['id'] for g in response.json()['groups']], [male.pk])
        response = self.client.get(reverse('get_teams'), {'sport': self.sport.pk, 'sexo': 0})
        self.assertEqual({t['id'] for t in response.json()['teams']}, {t.pk for t in self.teams})
        self.sport.fem = False
        self.sport.save()
        response = self.client.get(reverse('get_sexos'), {'sport': self.sport.pk})
        self.assertEqual([s['value'] for s in response.json()['sexos']], [0, 2])

    def test_malformed_lookup_inputs(self):
        for name in ('get_teams', 'get_groups', 'get_sexos'):
            self.assertEqual(self.client.get(reverse(name), {'sport': 'bad'}).status_code, 404)
        for name, key in (('get_teams', 'teams'), ('get_groups', 'groups')):
            response = self.client.get(reverse(name), {'sport': self.sport.pk, 'sexo': 'bad'})
            self.assertEqual(response.json()[key], [])

    def test_filter_controls_preserve_selection_and_clear_event(self):
        response = self.client.get(self.url, {'e': self.event.pk, 'sport': '0', 'genre': '0', 'q': 'Equipe'})
        self.assertContains(response, 'method="get" class="filter-menu"')
        self.assertContains(response, f'href="{self.url}?e={self.event.pk}" class="btn-clear"')
        self.assertContains(response, 'value="0" selected')
        self.assertContains(response, 'name="q" value="Equipe"')

    def test_error_form_preserves_values_and_allows_correction(self):
        response = self.post(time_b=self.teams[0].pk)
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'matches/create_errors.html')
        self.assertEqual(response.context['form']['location'].value(), 'Quadra A')
        self.assertEqual(self.post().status_code, 302)

    def test_scores_still_count_points_per_team(self):
        teams = list(self.match.teams.order_by('pk'))
        Point.objects.create(team_match=teams[0])
        Point.objects.create(team_match=teams[0])
        Point.objects.create(team_match=teams[1])
        response = self.client.get(self.url, {'e': self.event.pk})
        self.assertEqual((response.context['context'][0]['points_a'], response.context['context'][0]['points_b']), (2, 1))

    def test_search_location_and_id(self):
        self.match.location = 'Quadra azul'
        self.match.save()
        for query in ('Quadra azul', str(self.match.pk)):
            response = self.client.get(self.url, {'e': self.event.pk, 'q': query})
            self.assertEqual([row['match'].pk for row in response.context['context']], [self.match.pk])

    def test_existing_phase_and_group_creation(self):
        response = self.client.post(f'{self.url}?e={self.event.pk}', {'create_phase': '1', 'event_sport': self.sport.pk, 'name': 0, 'sexo_phase': 0})
        self.assertEqual(response.status_code, 302)
        phase = Phase.objects.get(event=self.sport)
        self.client.post(f'{self.url}?e={self.event.pk}', {'create_group': '1', 'phase': phase.pk, 'group_name': 'A'})
        self.assertTrue(Group_phase.objects.filter(phase=phase, name='A').exists())

    def test_start_match_and_block_second_live_match(self):
        # Isola publicação externa; a transição de estado continua real no banco.
        with patch('app.signals.channel_match'):
            response = self.client.post(self.url, {'change_match': self.match.pk})
        self.assertRedirects(response, reverse('scoreboard', args=[self.event.pk]), fetch_redirect_response=False)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, 1)
        another = Match.objects.create(event=self.event, sport=0)
        self.client.post(self.url, {'change_match': another.pk})
        another.refresh_from_db()
        self.assertEqual(another.status, 0)

    def test_no_view_permission_and_no_change_permission(self):
        self.restricted_user()
        self.assertRedirects(self.client.get(self.url), reverse('Home'), fetch_redirect_response=False)
        self.assertRedirects(self.client.post(self.url, {'change_match': self.match.pk}), reverse('Home'), fetch_redirect_response=False)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, 0)

    def test_actions_cannot_cross_event_boundary(self):
        self.restricted_user('view_match', 'change_match', 'add_phase', 'add_group_phase')
        sport = Event_sport.objects.create(event=self.other, sport=0)
        phase = Phase.objects.create(event=sport, sexo=0)
        actions = [{'change_match': self.foreign.pk}, {'sumula': self.foreign.pk},
                   {'create_phase': '1', 'event_sport': sport.pk, 'name': 0, 'sexo_phase': 0},
                   {'create_group': '1', 'phase': phase.pk, 'group_name': 'Inválido'}]
        for data in actions:
            with self.subTest(action=list(data)[0]):
                expected = 400 if 'create_phase' in data or 'create_group' in data else 404
                self.assertEqual(self.client.post(f'{self.url}?e={self.event.pk}', data).status_code, expected)

    def test_delete_requires_permission(self):
        self.restricted_user('view_match')
        response = self.client.post(reverse('matches_manage'), {'match_delete': self.match.pk})
        self.assertRedirects(response, reverse('Home'), fetch_redirect_response=False)
        self.assertTrue(Match.objects.filter(pk=self.match.pk).exists())

    def test_existing_delete_removes_match_and_team_links(self):
        pk = self.match.pk
        response = self.client.post(reverse('matches_manage'), {'match_delete': pk})
        self.assertRedirects(response, f'{self.url}?e={self.event.pk}', fetch_redirect_response=False)
        self.assertFalse(Match.objects.filter(pk=pk).exists())
        self.assertFalse(Team_match.objects.filter(match_id=pk).exists())

    def test_delete_last_volleyball_match_removes_set_control(self):
        volley = Volley_match.objects.create(event=self.event)
        match = Match.objects.create(event=self.event, sport=1, volley_match=volley)
        self.client.post(reverse('matches_manage'), {'match_delete': match.pk})
        self.assertFalse(Volley_match.objects.filter(pk=volley.pk).exists())

    def test_delete_one_set_preserves_other_matches(self):
        volley = Volley_match.objects.create(event=self.event)
        first = Match.objects.create(event=self.event, sport=1, volley_match=volley)
        second = Match.objects.create(event=self.event, sport=1, volley_match=volley)
        self.client.post(reverse('matches_manage'), {'match_delete': first.pk})
        self.assertTrue(Volley_match.objects.filter(pk=volley.pk).exists())
        self.assertTrue(Match.objects.filter(pk=second.pk).exists())


class CredentialRegressionTests(MatchFixtures, TestCase):
    def test_login_and_password_update_do_not_print_secrets(self):
        user = get_user_model().objects.create_user(username='synthetic-user', password='old-synthetic', type=3)
        output = StringIO()
        with redirect_stdout(output):
            response = self.client.post(reverse('user_manage'), {'user_id': user.pk, 'password': 'new-synthetic', 'active': 'on'})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('new-synthetic'))
        self.assertNotIn('new-synthetic', output.getvalue())
        self.assertNotIn(user.password, output.getvalue())
        self.client.logout()
        with redirect_stdout(output):
            response = self.client.post(reverse('login'), {'username': user.username, 'password': 'new-synthetic'})
        self.assertRedirects(response, reverse('Home'), fetch_redirect_response=False)
        self.assertNotIn('new-synthetic', output.getvalue())


class PhaseGroupValidationTests(MatchFixtures, TestCase):
    def test_event_required_for_phase_and_group(self):
        for data in ({'create_phase': '1', 'event_sport': self.sport.pk, 'name': 0, 'sexo_phase': 0},
                     {'create_group': '1', 'group_name': 'A'}):
            self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertFalse(Phase.objects.exists())
        self.assertFalse(Group_phase.objects.exists())

    def test_invalid_phase_input_does_not_write(self):
        url = f'{self.url}?e={self.event.pk}'
        data = {'create_phase': '1', 'event_sport': self.sport.pk, 'name': 0, 'sexo_phase': 0}
        foreign = Event_sport.objects.create(event=self.other, sport=0)
        self.sport.fem = False
        self.sport.save()
        for changes in ({'name': ''}, {'name': 'wrong'}, {'name': 99},
                        {'sexo_phase': 99}, {'sexo_phase': 1}, {'event_sport': foreign.pk}):
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post(url, {**data, **changes}).status_code, 400)
        self.assertFalse(Phase.objects.exists())

    def test_group_required_name_and_event_scope(self):
        phase = Phase.objects.create(event=self.sport, sexo=0)
        foreign = Phase.objects.create(event=Event_sport.objects.create(event=self.other, sport=0))
        data = {'create_group': '1', 'phase': phase.pk, 'group_name': 'A'}
        for changes in ({'phase': 'wrong'}, {'phase': foreign.pk}, {'group_name': '   '}, {'group_name': 'x' * 51}):
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post(f'{self.url}?e={self.event.pk}', {**data, **changes}).status_code, 400)
        self.assertFalse(Group_phase.objects.exists())

    def test_repeated_phase_and_group_do_not_duplicate(self):
        url = f'{self.url}?e={self.event.pk}'
        data = {'create_phase': '1', 'event_sport': self.sport.pk, 'name': 0, 'sexo_phase': 0}
        for _ in range(2):
            self.assertEqual(self.client.post(url, data).status_code, 302)
        phase = Phase.objects.get(event=self.sport)
        for _ in range(2):
            self.assertEqual(self.client.post(url, {'create_group': '1', 'phase': phase.pk, 'group_name': ' A '}).status_code, 302)
        self.assertEqual(Group_phase.objects.get(phase=phase).name, 'A')

    def test_phase_errors_preserve_action_and_event(self):
        response = self.client.post(f'{self.url}?e={self.event.pk}', {'create_phase': '1', 'name': 'bad'})
        self.assertContains(response, 'name="create_phase"', status_code=400)
        self.assertContains(response, f'action="{self.url}?e={self.event.pk}"', status_code=400)
