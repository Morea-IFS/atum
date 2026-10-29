#Loading The Libs
from dotenv import load_dotenv
load_dotenv()

import os
import sys
from pathlib import Path
from django.conf import settings
#!/usr/bin/env python3
"""
Script para configurar o arquivo jifs.service
"""

def get_input(prompt, default=None):
    """Obtém input do usuário com valor padrão"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def get_current_user():
    """Retorna o usuário atual do sistema"""
    import pwd
    return pwd.getpwuid(os.getuid()).pw_name


def get_current_group():
    """Retorna o grupo principal do usuário atual"""
    import grp
    import pwd
    return grp.getgrgid(pwd.getpwuid(os.getuid()).pw_gid).gr_name


def configure_service():
    """Configura o arquivo jifs.service"""
    
    print("=" * 60)
    print("Configuração do serviço JIFS")
    print("=" * 60)
    print()
    
    # Detectar valores padrão baseados no ambiente atual
    current_user = get_current_user()
    current_group = get_current_group()
    current_dir = os.getcwd()
    

    app_module = settings.WSGI_APPLICATION
    
    # Coletar informações do usuário
    print("1. Configuração de usuário e grupo:")
    user = current_user
    group = current_group
    
    print("\n2. Configuração de diretórios:")
    working_dir = current_dir
    
    # Validar se o diretório existe
    if not os.path.isdir(working_dir):
        print(f"AVISO: O diretório '{working_dir}' não existe!")
        create = get_input("Deseja continuar mesmo assim? (s/n)", default="s")
        if create.lower() != 's':
            print("Configuração cancelada.")
            sys.exit(1),
    
    # Caminho do virtualenv
    default_venv = os.path.join(working_dir, "env", "bin", "gunicorn")
    gunicorn_path = default_venv
    
    # Caminho do socket
    default_socket = os.path.join(os.path.dirname(working_dir), 
                                  "jifs-interclass", "sockets", "jifs.sock")
    socket_path = default_socket
    
    print("\nConfiguração do Gunicorn:")
    workers = get_input("Número de workers", default="3")
    log_level = get_input("Nível de log (debug/info/warning/error/critical)", 
                         default="info")
    
    
    
    
    # Criar o conteúdo do arquivo de serviço
    service_content = f"""#/etc/systemd/system/jifs.service

[Unit]
Description=JIIFS daemon
After=network.target

[Service]
Type=notify
# the specific user that our service will run as
User={user}
Group={group}
# another option for an even more restricted service is
# DynamicUser=yes
# see http://0pointer.net/blog/dynamic-users-with-systemd.html
RuntimeDirectory=gunicorn
WorkingDirectory={working_dir}
ExecStart={gunicorn_path} \\
    --workers {workers} \\
    --log-level {log_level} \\
    --bind unix:{socket_path} \\
    interclasse.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""
    
    # Determinar o caminho de saída
    output_file = os.path.join(current_dir, "conf", "root", "jifs.service")
    
    print("\n" + "=" * 60)
    print("Resumo da configuração:")
    print("=" * 60)
    print(f"Usuário: {user}")
    print(f"Grupo: {group}")
    print(f"Diretório de trabalho: {working_dir}")
    print(f"Gunicorn: {gunicorn_path}")
    print(f"Socket: {socket_path}")
    print(f"Workers: {workers}")
    print(f"Log Level: {log_level}")
    print(f"Módulo WSGI: {app_module}")
    print(f"Arquivo de saída: {output_file}")
    print("=" * 60)
    print()
    
    # Mostrar preview do arquivo
    print("Preview do arquivo a ser gerado:")
    print("-" * 60)
    print(service_content)
    print("-" * 60)
    print()
    
    # Confirmar antes de salvar
    confirm = get_input("Deseja salvar este arquivo? (s/n)", default="s")
    if confirm.lower() != 's':
        print("Configuração cancelada.")
        sys.exit(0)
    
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Salvar o arquivo
    with open(output_file, 'w') as f:
        f.write(service_content)
    
    print(f"\n✓ Arquivo salvo com sucesso em: {output_file}")
    
    # Instruções pós-configuração
    print("\n" + "=" * 60)
    print("Próximos passos:")
    print("=" * 60)
    print("1. Copie o arquivo para o diretório systemd:")
    print(f"   sudo cp {output_file} /etc/systemd/system/jifs.service")
    print()
    print("2. Recarregue o systemd:")
    print("   sudo systemctl daemon-reload")
    print()
    print("3. Ative o serviço:")
    print("   sudo systemctl enable jifs.service")
    print()
    print("4. Inicie o serviço:")
    print("   sudo systemctl start jifs.service")
    print()
    print("5. Verifique o status:")
    print("   sudo systemctl status jifs.service")
    print("=" * 60)


def main():
    """Função principal"""
    try:
        configure_service()
    except KeyboardInterrupt:
        print("\n\nConfiguração cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro durante a configuração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
