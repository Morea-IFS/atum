from unittest import expectedFailure

from django.contrib.auth.models import Permission
from django.test import TestCase

from .models import CustomUser, Event


class BaseTestCase(TestCase):
    """Cria um evento e oferece um login pela própria página /login."""

    @classmethod
    def setUpTestData(cls):
        cls.dono = CustomUser.objects.create_user(username="dono", password="senha-teste", type=1)
        cls.evento = Event.objects.create(
            name="Evento de teste",
            logo="defaults/logo-ifs.svg",
            user=cls.dono,
            general_need_terms=False,
        )

    def criar_usuario(self, username, tipo, evento=True):
        return CustomUser.objects.create_user(
            username=username,
            password="senha-teste",
            type=tipo,
            event_user=self.evento if evento else None,
        )

    def entrar(self, usuario):
        # Login pela página /login, e não com force_login: o signal on_user_logged_in
        # lê request.user_agent, que só existe numa requisição que passa pelos middlewares.
        resposta = self.client.post("/login", {"username": usuario.username, "password": "senha-teste"})
        self.assertEqual(resposta.status_code, 302, "o login deveria redirecionar")


class PaginasPublicasTests(BaseTestCase):
    """As páginas abertas ao público respondem sem erro."""

    def test_lista_de_eventos(self):
        Event.objects.create(name="Outro evento", logo="defaults/logo-ifs.svg", user=self.dono)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_com_um_evento_so_vai_direto_para_ele(self):
        resposta = self.client.get("/")
        self.assertRedirects(resposta, f"/{self.evento.id}")

    def test_pagina_do_evento(self):
        self.assertEqual(self.client.get(f"/{self.evento.id}").status_code, 200)

    def test_chaveamento(self):
        self.assertEqual(self.client.get(f"/chaveamento/{self.evento.id}").status_code, 200)

    def test_placar(self):
        self.assertEqual(self.client.get(f"/placar/{self.evento.id}").status_code, 200)

    def test_sobre(self):
        self.assertEqual(self.client.get(f"/sobre/{self.evento.id}").status_code, 200)

    def test_pagina_de_login(self):
        self.assertEqual(self.client.get("/login").status_code, 200)


class LoginObrigatorioTests(BaseTestCase):
    """Páginas internas mandam o visitante anônimo para o login."""

    rotas_protegidas = [
        "/morea-admin",
        "/manage/match",
        "/manage/player",
        "/manage/event",
        "/manage/banner",
        "/settings",
        "/faq_manage",
    ]

    def test_anonimo_vai_para_o_login(self):
        for rota in self.rotas_protegidas:
            with self.subTest(rota=rota):
                resposta = self.client.get(rota)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta["Location"].startswith("/login"), resposta["Location"])

    @expectedFailure
    def test_anonimo_nas_rotas_com_time_restriction_vai_para_o_login(self):
        # Bug (issue #78): em team_manage, team_players_manage e voluntary_manage (app/views.py), o @time_restriction()
        # está acima do @login_required, então roda primeiro e lê request.user.type de um AnonymousUser (erro 500).
        for rota in ["/manage/team", "/manage/team/player/1", "/manage/voluntary"]:
            with self.subTest(rota=rota):
                resposta = self.client.get(rota)
                self.assertEqual(resposta.status_code, 302)


class PermissaoTests(BaseTestCase):
    """Uma view com @permission_required barra quem não tem a permissão."""

    def test_sem_permissao_volta_para_o_painel(self):
        # O handler403 do projeto (erro_403_customizado) mostra um aviso e redireciona para o painel.
        usuario = self.criar_usuario("marcador", tipo=3)
        self.entrar(usuario)
        resposta = self.client.get("/faq_manage")
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta["Location"], "/morea-admin")

    def test_com_permissao_entra(self):
        usuario = self.criar_usuario("marcador", tipo=3)
        usuario.user_permissions.add(Permission.objects.get(codename="view_help"))
        self.entrar(usuario)
        self.assertEqual(self.client.get("/faq_manage").status_code, 200)


class UsuarioSemEventoTests(BaseTestCase):
    """
    Bugs conhecidos da issue #75: usuário sem evento vinculado quebra o sistema.
    Marcados com @expectedFailure: o CI fica verde enquanto o bug existir.
    Quando alguém corrigir, o teste passa a acusar "unexpected success": é a hora de tirar o decorator.
    """

    @expectedFailure
    def test_usuario_comum_sem_evento_pode_ser_criado(self):
        # app/signals.py:590 (set_type_for_staff) acessa event_user.enrollment_init sem conferir se existe
        self.criar_usuario("comum_sem_evento", tipo=2, evento=False)

    @expectedFailure
    def test_admin_sem_evento_abre_o_painel(self):
        # app/decorators.py:56 (terms_accept_required) acessa event_user.general_need_terms antes de conferir
        usuario = self.criar_usuario("admin_sem_evento", tipo=0, evento=False)
        self.entrar(usuario)
        self.assertEqual(self.client.get("/morea-admin").status_code, 200)

    @expectedFailure
    def test_marcador_sem_evento_abre_o_painel(self):
        # app/views.py:720 (home_admin) faz Event.objects.get(id=user.event_user.id)
        usuario = self.criar_usuario("marcador_sem_evento", tipo=3, evento=False)
        self.entrar(usuario)
        self.assertEqual(self.client.get("/morea-admin").status_code, 200)

    @expectedFailure
    def test_marcador_sem_evento_abre_gestao_de_times(self):
        # app/decorators.py:23 (time_restriction) faz Event.objects.get(id=request.user.event_user.id)
        usuario = self.criar_usuario("marcador_sem_evento", tipo=3, evento=False)
        self.entrar(usuario)
        self.assertNotEqual(self.client.get("/manage/team").status_code, 500)
