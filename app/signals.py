# app/signals.py
from django.db.models.signals import post_save, post_delete, pre_delete, post_migrate
from django.dispatch import receiver
from django.conf import settings
from django.templatetags.static import static
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import Group, Permission
from .generators import generate_timer
from django.contrib.auth import get_user_model
from .models import Point, Match, Team_match, Team, Penalties, Volley_match, Player_match, Time_pause, Banner, Occurrence, UserSession, Player, ActivityLog
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import datetime
import pytz

import logging
logger = logging.getLogger(__name__)

def safe_group_send(group, payload):
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(group, payload)
    except Exception:
        logger.exception("Falha ao enviar para o grupo %s", group)

User = get_user_model()
default_photo_url = f"{settings.MEDIA_URL}defaults/team.png"

@receiver(post_save, sender=Player)
def log_player_save(sender, instance, created, **kwargs):
    ActivityLog.objects.create(
        user=instance.admin, 
        action='CREATE' if created else 'UPDATE',
        model_name='Player',
        object_name=str(instance)
    )

@receiver(post_delete, sender=Player)
def log_player_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=instance.admin,
        action='DELETE',
        model_name='Player',
        object_name=str(instance)
    )

def serialize_players(players_qs):
    result = []
    for i in players_qs:
        result.append({
            "name": i.player.name,
            "photo_url": i.player.photo.url if i.player.photo else default_photo_url,
            "funcao": i.get_activity_display(),
            "number": getattr(i, 'player_number', None),
        })
    return result

def serialize_players_match(players_qs):
    result = []
    for i in players_qs:
        if not i.activity in [0, 1]:
            result.append({
                "name": i.player.name,
                "photo_url": i.player.photo.url if i.player.photo else default_photo_url,
                "funcao": i.get_activity_display(),
            })
    return result

def serialize_occurrence(occurrence):
    result = []
    for i in occurrence:
        match i.name:
            case "Cartão Vermelho": img = 'icon-red-card.png'
            case "Cartão Amarelo": img = 'icon-yellow-card.png'
            case "Assistência": img = 'icon-assis-to.png'
            case "Falta": img = 'icon-whistle.png'
            case _: img = 'icon-ball.png'
        result.append({
            "name": i.name,
            "details": i.details,
            "img": f'/static/images/{img}',
        })
    return result

@receiver([post_save, post_delete], sender=Team)
def team_updated(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nos team :)")
    if Match.objects.filter(status=1, event=instance.event):
        match_data, match_public = send_scoreboard_team(instance)
        if match_data is None:
            return
        safe_group_send(
            f'scoreboard_{instance.event.id}',
            {
                'type': 'team_new',
                'match': match_data,
            }
        )
        safe_group_send(
            f'public_{instance.event.id}',
            {
                'type': 'team_new',
                'match': match_public,
            }
        )

def send_scoreboard_team(instance):
    event = instance.event
    if settings.DEBUG: print("eita, mudanças (team) sendo preparadas. :)")
    if Match.objects.filter(status=1, event=event):
        match = Match.objects.get(status=1, event=event)
        if Team_match.objects.filter(team=instance, match__status=1, team__event=match.event):
            match = Match.objects.get(status=1, event=event)
            team_matchs = Team_match.objects.filter(match=match)
            if len(team_matchs) < 2:
                return None, None
            if match.volley_match:
                if (match.volley_match.sets_team_a + match.volley_match.sets_team_b) % 2 == 0:
                    team_match_a = team_matchs[0]
                    team_match_b = team_matchs[1]
                else:
                    team_match_a = team_matchs[1]
                    team_match_b = team_matchs[0]
            else:
                team_match_a = team_matchs[0]
                team_match_b = team_matchs[1]
            match_public = {
                'photoA': team_match_a.team.photo.url if team_match_a.team.photo else default_photo_url,
                'photoB': team_match_b.team.photo.url if team_match_b.team.photo else default_photo_url,
                'team_name_a': team_match_a.team.name,
                'team_name_b': team_match_b.team.name,
                'colorA': team_match_a.team.color,
                'colorB': team_match_b.team.color,
            }
        else:
            match_public = {
                'team_name_a': "TEAM A",
                'team_name_b': "TEAM B",
                'colorA': "#000ed3",
                'colorB': "#ff0000",
                'photoA': default_photo_url,
                'photoB': default_photo_url,
            }
    else:
        match_public = {
            'team_name_a': "TEAM A",
            'team_name_b': "TEAM B",
            'colorA': "#000ed3",
            'colorB': "#ff0000",
            'photoA': default_photo_url,
            'photoB': default_photo_url,
        }

    match_data = match_public

    if settings.DEBUG: print("eita, saindo signals (team) sendo preparadas. :)")
    if settings.DEBUG: print(match_public)
    return match_data, match_public

@receiver([post_save, post_delete], sender=Point)
def point_changed(sender, instance, created=False, using=None, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nos pontos :)")
    match_data, match_public = send_scoreboard_point(instance, created)
    if match_data is None:
        return
    safe_group_send(
        f'scoreboard_{instance.team_match.match.event.id}',
        {
            'type': 'point_new',
            'match': match_data,
        }
    )
    safe_group_send(
        f'public_{instance.team_match.match.event.id}',
        {
            'type': 'point_new',
            'match': match_public,
        }
    )

def send_scoreboard_point(instance, created):
    event = instance.team_match.match.event
    if settings.DEBUG: print("eita, mudanças (pontos) sendo preparadas. :)")
    if Match.objects.filter(status=1, event=event):
        match = Match.objects.get(status=1, event=event)
        team_matchs = Team_match.objects.filter(match=match)
        if len(team_matchs) < 2:
            return None, None
        if match.volley_match:
            if (match.volley_match.sets_team_a + match.volley_match.sets_team_b) % 2 == 0:
                team_match_a = team_matchs[0]
                team_match_b = team_matchs[1]
            else:
                team_match_a = team_matchs[1]
                team_match_b = team_matchs[0]
        else:
            team_match_a = team_matchs[0]
            team_match_b = team_matchs[1]


        if match.sport == 0:
            point_a = Point.objects.filter(team_match=team_match_a).count() - Point.objects.filter(point_types=2, team_match=team_match_a).count()
            point_b = Point.objects.filter(team_match=team_match_b).count() - Point.objects.filter(point_types=2, team_match=team_match_b).count()
        else:
            point_a = Point.objects.filter(team_match=team_match_a).count()
            point_b = Point.objects.filter(team_match=team_match_b).count()

        point = Point.objects.filter(team_match__match=match).last()

        match_data = {
            'point_a': point_a,
            'point_b': point_b,
            'colorA': team_match_a.team.color,
            'colorB': team_match_b.team.color,
            'sport': match.get_sport_display(),
        }
        if match.volley_match:
            match_data['aces_a'] = Point.objects.filter(point_types=2, team_match=team_match_a).count()
            match_data['aces_b'] = Point.objects.filter(point_types=2, team_match=team_match_b).count()
            
        elif match.sport == 0:
            match_data['penalties_a'] = Point.objects.filter(point_types=2, team_match=team_match_a).count()
            match_data['penalties_b'] = Point.objects.filter(point_types=2, team_match=team_match_b).count()

        if point and created and point.player and point.team_match and point.point_types == 0:
            if point.team_match == team_match_a:
                team_letter = 'A'
                team_color = team_match_a.team.color
            else:
                team_letter = 'B' 
                team_color = team_match_b.team.color
            
            match_data['team'] = team_letter 
            match_data['team_name'] = point.team_match.team.name if point.team_match.team.name else "TEAM"
            match_data['team_img'] = point.team_match.team.photo.url if point.team_match.team.photo else default_photo_url
            match_data['player_name'] = point.player.name if point.player.name else "PLAYER"
            if point.player.photo_goal:
                match_data['player_img'] = point.player.photo_goal.url 
            else:
                match_data['player_img'] = point.player.photo.url if point.player.photo else default_photo_url
            match_data['colorA'] = team_match_a.team.color
            match_data['colorB'] = team_match_b.team.color
    
    else:
        match_data = {
            'point_a': 0,
            'point_b': 0,
            'colorA': "#000ed3", 
            'colorB': "#ff0000",
            'sport': "Nenhum",
        }   
    
    match_public = match_data
    if settings.DEBUG: print("eita, saindo signals (pontos) sendo preparadas. :)")
    if settings.DEBUG: print(match_data)
    return match_data, match_public


@receiver([post_save, post_delete], sender=Time_pause)
def time_pause_changed(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças no (tempo) :)")
    channel_layer = get_channel_layer()
    match_data, match_public = send_scoreboard_time(instance)
    safe_group_send(
        f'scoreboard_{instance.match.event.id}',
        {
            'type': 'time_new',
            'match': match_data,
        }
    )
    safe_group_send(
        f'public_{instance.match.event.id}',
        {
            'type': 'time_new',
            'match': match_public,
        }
    )

def send_scoreboard_time(instance):
    event = instance.match.event
    match_data = {'seconds': 0, 'status': 0}
    if settings.DEBUG: print("eita, mudanças (tempo) sendo preparadas. :)")
    if Match.objects.filter(status=1, event=event):
        match = Match.objects.get(status=1, event=event)
        seconds, status = generate_timer(match)

        match_data = {
            'seconds': seconds,
            'status': status,
        }

    match_public = match_data

    if settings.DEBUG: print("eita, saindo signals (tempo) sendo preparadas. :)")
    if settings.DEBUG: print(match_data)
    return match_data, match_public

@receiver([post_save, post_delete], sender=Banner)
def banner_changed(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nas banner :)")
    channel_layer = get_channel_layer()
    match_data = send_scoreboard_banner(instance)
    safe_group_send(
        f'scoreboard_{instance.event.id}',
        {
            'type': 'banner_new',
            'match': match_data,
        }
    )

def send_scoreboard_banner(instance):
    if settings.DEBUG: print("eita, mudanças (banner) sendo preparadas. :)")
    match_data = {}
    event = instance.event
    if Banner.objects.filter(status=0, event=event).exists(): 
        match_data['status'] = 1
        match_data['banner'] = Banner.objects.filter(status=0, event=event)[0].image.url
    else:
        match_data['status'] = 0
    if settings.DEBUG: print("eita, saindo signals (banner) sendo preparadas. :)")
    if settings.DEBUG: print(match_data)
    return match_data

@receiver([post_save, post_delete], sender=Penalties)
def penalties_updated(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nas penalidades :)")
    match_data, match_public = send_scoreboard_penalties(instance)
    if match_data is None:
        return
    safe_group_send(
        f'scoreboard_{instance.team_match.match.event.id}',
        {
            'type': 'penalties_new',
            'match': match_data,
        }
    )
    safe_group_send(
        f'public_{instance.team_match.match.event.id}',
        {
            'type': 'penalties_new',
            'match': match_public,
        }
    )

def send_scoreboard_penalties(instance):
    event = instance.team_match.match.event
    if settings.DEBUG: print("eita, mudanças (penalidades) sendo preparadas. :)")
    if Match.objects.filter(status=1, event=event):
        match = Match.objects.get(status=1, event=event)
        team_matchs = Team_match.objects.filter(match=match)
        if len(team_matchs) < 2:
            return None, None
        if match.volley_match:
            if (match.volley_match.sets_team_a + match.volley_match.sets_team_b) % 2 == 0:
                team_match_a = team_matchs[0]
                team_match_b = team_matchs[1]
            else:
                team_match_a = team_matchs[1]
                team_match_b = team_matchs[0]
        else:
            team_match_a = team_matchs[0]
            team_match_b = team_matchs[1]

        lack_a = Penalties.objects.filter(type_penalties=2, team_match=team_match_a).count()
        lack_b = Penalties.objects.filter(type_penalties=2, team_match=team_match_b).count()
        card_a = Penalties.objects.filter(type_penalties=0, team_match=team_match_a).count() + Penalties.objects.filter(type_penalties=1, team_match=team_match_a).count()
        card_b = Penalties.objects.filter(type_penalties=0, team_match=team_match_b).count() + Penalties.objects.filter(type_penalties=1, team_match=team_match_b).count()

        match_data = {
            'lack_a': lack_a,
            'lack_b': lack_b,
            'card_a': card_a,
            'card_b': card_b,
        }
        if instance.player:
            print(instance.type_penalties)
            match_data['penalties_player'] = instance.player.name
            if instance.type_penalties == 0: match_data['penalties_url'] = static('images/card-red.png')
            elif instance.type_penalties == 1: match_data['penalties_url'] = static('images/card-yellow.png')
            else: match_data['penalties_url'] = static('images/whistle.png')
    else:
        match_data = {
            'lack_a': 0,
            'lack_b': 0,
            'card_a': 0,
            'card_b': 0,
        }   
    
    match_public = match_data
    
    if settings.DEBUG: print("eita, saindo signals (penalidades) sendo preparadas. :)")
    if settings.DEBUG: print(match_data)
    return match_data, match_public

@receiver([post_save, post_delete], sender=Occurrence)
def occurrence_updated(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nas penalidades :)")
    channel_layer = get_channel_layer()
    match_public = send_scoreboard_occurrence(instance)
    safe_group_send(
        f'public_{instance.match.event.id}',
        {
            'type': 'occurrence_new',
            'match': match_public,
        }
    )

def send_scoreboard_occurrence(instance):
    event = instance.match.event
    if settings.DEBUG: print("eita, mudanças (penalidades) sendo preparadas. :)")
    if Match.objects.filter(status=1, event=event):
        match = Match.objects.get(status=1, event=event)
        occurrence = Occurrence.objects.filter(match=match).order_by('-datetime')[:10]
    else:
        match = Match.objects.filter(event=event).last()
        occurrence = Occurrence.objects.filter(match=match).order_by('-datetime')[:10]
    match_public = {
        'occurrence': serialize_occurrence(occurrence),
    }
    
    if settings.DEBUG: print("eita, saindo signals (penalidades) sendo preparadas. :)")
    if settings.DEBUG: print(match_public)
    return match_public

@receiver([post_save, post_delete], sender=Volley_match)
def volley_updated(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nas partidas de vôlei :)")
    if instance.status == 1:
        channel_match(instance)

@receiver([post_save, post_delete], sender=Match)
def match_updated(sender, instance, using, **kwargs):
    if settings.DEBUG: print("hmm, mudanças nas partidas :)")
    if instance.status == 1:
        channel_match(instance)

def channel_match(instance):
    match_data, match_public = send_scoreboard_match(instance)
    if match_data is None:
        return
    safe_group_send(
        f'scoreboard_{instance.event.id}',
        {
            'type': 'match_new',
            'match': match_data,
        }
    )
    safe_group_send(
        f'public_{instance.event.id}',
        {
            'type': 'match_new',
            'match': match_public,
        }
    )

def send_scoreboard_match(instance):
    if settings.DEBUG: print("eita, mudanças (partidas) sendo preparadas. :)")
    match = None
    event = instance.event
    if Volley_match.objects.filter(status=1, event=event).exists():
        volley_match = Volley_match.objects.get(status=1, event=event)
        if Match.objects.filter(volley_match=volley_match, status=1, event=event).exists():
            match = Match.objects.get(volley_match=volley_match, status=1, event=event)
    elif Match.objects.filter(status=1, event=event):
        match = Match.objects.get(status=1, event=event)
        seconds, status = generate_timer(match)
    if match:
        team_matchs = Team_match.objects.filter(match=match)
        if len(team_matchs) < 2:
            return None, None

        if match.volley_match:
            if (match.volley_match.sets_team_a + match.volley_match.sets_team_b) % 2 == 0:
                team_match_a = team_matchs[0]
                team_match_b = team_matchs[1]
                sets_a = match.volley_match.sets_team_a
                sets_b = match.volley_match.sets_team_b
            else:
                team_match_a = team_matchs[1]
                team_match_b = team_matchs[0]
                sets_b = match.volley_match.sets_team_a
                sets_a = match.volley_match.sets_team_b
            ball_sport = static('images/ball-of-volley.png')
        else:
            team_match_a = team_matchs[0]
            team_match_b = team_matchs[1]
            if match.sport == 3: ball_sport = static('images/ball-of-handball.png')
            else: ball_sport = static('images/ball-of-futsal.png')

        if match.sport == 0:
            point_a = Point.objects.filter(team_match=team_match_a).count() - Point.objects.filter(point_types=2, team_match=team_match_a).count()
            point_b = Point.objects.filter(team_match=team_match_b).count() - Point.objects.filter(point_types=2, team_match=team_match_b).count()
        else:
            point_a = Point.objects.filter(team_match=team_match_a).count()
            point_b = Point.objects.filter(team_match=team_match_b).count()
        lack_a = Penalties.objects.filter(type_penalties=2, team_match=team_match_a).count()
        lack_b = Penalties.objects.filter(type_penalties=2, team_match=team_match_b).count()
        card_a = Penalties.objects.filter(type_penalties=0, team_match=team_match_a).count() + Penalties.objects.filter(type_penalties=1, team_match=team_match_a).count()
        card_b = Penalties.objects.filter(type_penalties=0, team_match=team_match_b).count() + Penalties.objects.filter(type_penalties=1, team_match=team_match_b).count()

        match_data = {
            'team_name_a': team_match_a.team.name,
            'team_name_b': team_match_b.team.name,
            'match_sexo': match.get_sexo_display(),
            'match_sport': match.get_sport_display(),
            'point_a': point_a,
            'ball_sport': ball_sport,
            'point_b': point_b,
            'lack_a': lack_a,
            'lack_b': lack_b,
            'card_a': card_a,
            'card_b': card_b,
            'colorA': team_match_a.team.color,
            'colorB': team_match_b.team.color,
            'detailed': match.get_detailed_display(),
            'photoA': team_match_a.team.photo.url if team_match_a.team.photo else default_photo_url,
            'photoB': team_match_b.team.photo.url if team_match_b.team.photo else default_photo_url,
        }

        if match.volley_match:
            match_data['sets_a'] = sets_a
            match_data['sets_b'] = sets_b
            match_data['aces_a'] = Point.objects.filter(point_types=2, team_match=team_match_a).count()
            match_data['aces_b'] = Point.objects.filter(point_types=2, team_match=team_match_b).count()
        else:
            match_data['seconds'] = seconds
            match_data['status'] = status

        if match.sport == 0:
            match_data['penalties_a'] = Point.objects.filter(point_types=2, team_match=team_match_a).count()
            match_data['penalties_b'] = Point.objects.filter(point_types=2, team_match=team_match_b).count()

        if match.detailed == 5: 
            players_a = Player_match.objects.filter(team_match=team_match_a)
            players_b = Player_match.objects.filter(team_match=team_match_b)
            
            lineup = {
                'players_a': serialize_players_match(players_a),
                'players_b': serialize_players_match(players_b),
            }
            match_data['lineup'] = lineup

        players_a_qs = Player_match.objects.filter(team_match=team_match_a)
        players_b_qs = Player_match.objects.filter(team_match=team_match_b)

        match_public = match_data
        
        match_public['players_a'] = serialize_players(players_a_qs)
        match_public['players_b'] = serialize_players(players_b_qs)
        
    else:
        match_data = {
            'team_name_a': "TEAM A",
            'team_name_b': "TEAM B",
            'match_sexo': "Nenhum",
            'match_sport': "Nenhum",
            'point_a': 0,
            'point_b': 0,
            'lack_a': 0,
            'lack_b': 0,
            'card_a': 0,
            'card_b': 0,
            'colorA': "#FF0000",
            'colorB': "#0000FF",
            'photoA': default_photo_url,
            'photoB': default_photo_url,
        }   

        match_public = match_data

    if settings.DEBUG: print("eita, saindo signals (partidas) sendo preparadas. :)")
    return match_data, match_public

@receiver(post_save, sender=User)
def set_type_for_staff(sender, instance, created, **kwargs):
    brasilia_tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(brasilia_tz)
    if settings.DEBUG: print("chegouuu")
    if created and instance.is_staff:
        instance.type = 0
        instance.save()
    elif int(instance.type) == 1:
        group_name = "event coordinator"
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.groups.add(group)
    elif int(instance.type) == 2 and (instance.event_user.enrollment_init <= now <= instance.event_user.enrollment_end):
        group_name = "add user common"
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.groups.add(group)
    elif int(instance.type) == 2:
        group_name = "user common"
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.groups.add(group)
    elif int(instance.type) == 3:
        group_name = "score marker"
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.groups.add(group)
    else:
        if settings.DEBUG: print(instance.type, " - ", type(instance.type), " - ", type(int(instance.type)))
    

@receiver(post_migrate)
def create_user_common_group(sender, **kwargs):
    if sender.name != "app":  
        return

    group_name = "event coordinator"
    group, created = Group.objects.get_or_create(name=group_name)

    # Lista de permissões que você quer adicionar
    permission_codenames = [
        "view_attachments",
        "view_event_sport",
        "view_help",

        "view_team",
        "add_team",
        
        "view_event",

        "add_player",
        "change_player",
        "delete_player",
        "view_player",

        "add_customuser",
        "change_customuser",
        "delete_customuser",
        "view_customuser",

        "add_player_team_sport",
        "change_player_team_sport",
        "delete_player_team_sport",
        "view_player_team_sport",

        "add_team_sport",
        "change_team_sport",
        "delete_team_sport",
        "view_team_sport",
        
        "add_voluntary",
        "change_voluntary",
        "delete_voluntary",
        "view_voluntary",

        "add_match",
        "change_match",
        "delete_match",
        "view_match",

        "add_phase",
        "change_phase",
        "delete_phase",
        "view_phase",

        "add_group_phase",
        "change_group_phase",
        "delete_group_phase",
        "view_group_phase",

        "add_point",
        "add_assistance",
        "add_penalties",
        
    ]

    permissions = Permission.objects.filter(codename__in=permission_codenames)

    if permissions.exists():
        group.permissions.set(permissions)
        if settings.DEBUG: print(f"✅ Grupo '{group_name}' criado/atualizado com permissões.")
    else:
        if settings.DEBUG: print("⚠️ Nenhuma permissão encontrada. Verifique os codenames.")


    group_name = "add user common"
    group, created = Group.objects.get_or_create(name=group_name)

    # Lista de permissões que você quer adicionar
    permission_codenames = [
        "view_attachments",
        "view_event_sport",
        "view_help",
        "view_match",

        "add_player",
        "change_player",
        "delete_player",
        "view_player",

        "add_voluntary",
        "change_voluntary",
        "delete_voluntary",
        "view_voluntary",

        "add_player_team_sport",
        "change_player_team_sport",
        "delete_player_team_sport",
        "view_player_team_sport",

        "add_team_sport",
        "change_team_sport",
        "delete_team_sport",
        "view_team_sport",

    ]

    permissions = Permission.objects.filter(codename__in=permission_codenames)

    if permissions.exists():
        group.permissions.set(permissions)
        if settings.DEBUG: print(f"✅ Grupo '{group_name}' criado/atualizado com permissões.")
    else:
        if settings.DEBUG: print("⚠️ Nenhuma permissão encontrada. Verifique os codenames.")

    group_name = "user common"
    group, created = Group.objects.get_or_create(name=group_name)

    # Lista de permissões que você quer adicionar
    permission_codenames = [
        "view_attachments",
        "view_event_sport",
        "view_help",
        "view_match",

        "view_player",

        "view_voluntary",

        "view_player_team_sport",

        "view_team_sport",

    ]

    permissions = Permission.objects.filter(codename__in=permission_codenames)

    if permissions.exists():
        group.permissions.set(permissions)
        if settings.DEBUG: print(f"✅ Grupo '{group_name}' criado/atualizado com permissões.")
    else:
        if settings.DEBUG: print("⚠️ Nenhuma permissão encontrada. Verifique os codenames.")

    group_name = "edit user common"
    group, created = Group.objects.get_or_create(name=group_name)

    permission_codenames = [
        "view_attachments",
        "view_event_sport",
        "view_help",
        "view_match",

        "change_player",
        "delete_player",
        "view_player",

        "change_voluntary",
        "delete_voluntary",
        "view_voluntary",

        "change_player_team_sport",
        "delete_player_team_sport",
        "view_player_team_sport",

        "change_team_sport",
        "delete_team_sport",
        "view_team_sport",

    ]

    permissions = Permission.objects.filter(codename__in=permission_codenames)

    if permissions.exists():
        group.permissions.set(permissions)
        if settings.DEBUG: print(f"✅ Grupo '{group_name}' criado/atualizado com permissões.")
    else:
        if settings.DEBUG: print("⚠️ Nenhuma permissão encontrada. Verifique os codenames.")

    group_name = "score marker"
    group, created = Group.objects.get_or_create(name=group_name)

    permission_codenames = [
        "view_volley_match",
        "view_match",

        "add_point",
        "add_assistance",

    ]

    permissions = Permission.objects.filter(codename__in=permission_codenames)

    if permissions.exists():
        group.permissions.set(permissions)
        if settings.DEBUG: print(f"✅ Grupo '{group_name}' criado/atualizado com permissões.")
    else:
        if settings.DEBUG: print("⚠️ Nenhuma permissão encontrada. Verifique os codenames.")

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")

@user_logged_in.connect
def on_user_logged_in(sender, request, user, **kwargs):
    session_key = request.session.session_key
    session = Session.objects.get(session_key=session_key)
    ip = get_client_ip(request)
    device = request.user_agent.device.family
    browser = request.user_agent.browser.family
    os = request.user_agent.os.family


    UserSession.objects.update_or_create(
        session=session,
        defaults={
            "user": user,
            "ip_address": ip,
            "device": device,
            "browser": browser,
            "os": os,
            "last_activity": timezone.now(),
        }
    )

