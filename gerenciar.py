import os
import shutil
from database import FaceDatabase

DATASET_DIR = "dataset"


def editar_nome(db):
    users = db.get_all_users()
    if not users:
        print("\nNenhum usuario cadastrado!")
        return

    print("\nSELECIONE O USUÁRIO PARA RENOMEAR:")
    for user in users:
        u_id = user[0] if isinstance(user, (tuple, list)) else user.get('id')
        u_nome = user[1] if isinstance(user, (tuple, list)) else user.get('nome')
        print(f"   [ID: {u_id}] {u_nome}")

    try:
        user_id = int(input("\nDigite o ID do usuario: "))
    except ValueError:
        print("ID invalido!")
        return

    # Busca o usuário pelo ID selecionado
    user = next((u for u in users if (u[0] if isinstance(u, (tuple, list)) else u.get('id')) == user_id), None)

    if not user:
        print("Usuario nao encontrado!")
        return

    old_name = user[1] if isinstance(user, (tuple, list)) else user.get('nome')

    entrada = input(f"Digite o NOVO nome para '{old_name}': ").strip()
    novo_nome = "_".join(entrada.lower().split())

    if not novo_nome:
        print("O nome nao pode ser vazio!")
        return

    # ATENÇÃO: Passe o user_id (ou garanta que seu método no DB atualize corretamente por ID/nome)
    # Se seu db.update_user_name aceitar (user_id, novo_nome), prefira usar user_id.
    if db.update_user_name(user_id, novo_nome) if hasattr(db, 'update_user_name') else db.update_user_name(old_name, novo_nome):
        
        # Renomeia a pasta do dataset caso ela exista
        old_path = os.path.join(DATASET_DIR, old_name)
        new_path = os.path.join(DATASET_DIR, novo_nome)

        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"Pasta renomeada para '{novo_nome}'")

        print(f"Nome alterado com sucesso para '{novo_nome}'!")
    else:
        print("Erro ao renomear no banco de dados.")


def listar_cadastros(db):
    users = db.get_all_users()
    if not users:
        print("\nNenhum usuario cadastrado!")
        input("\nPressione [Enter] para continuar...")
        return

    print("\nUSUÁRIOS CADASTRADOS NO SQLITE:")
    print("-" * 45)
    for user in users:
        user_id = user[0] if isinstance(user, (tuple, list)) else user.get('id')
        raw_name = user[1] if isinstance(user, (tuple, list)) else user.get('nome')
        
        # Exibe o nome que está gravado atualmente no banco
        name = str(raw_name) if raw_name else "sem_nome"
        
        caminho_pasta = os.path.join(DATASET_DIR, name)
        info_fotos = ""
        
        if os.path.exists(caminho_pasta):
            num_fotos = len(os.listdir(caminho_pasta))
            info_fotos = f" ({num_fotos} fotos em disco)"

        print(f"   [ID: {user_id}] {name}{info_fotos}")
        
    print("-" * 45)
    input("\nPressione [Enter] para continuar...")

def apagar_cadastro(db):
    users = db.get_all_users()
    if not users:
        print("\nNenhum usuario cadastrado!")
        return

    print("\nSELECIONE O USUARIO PARA APAGAR:")
    for user in users:
        print(f"  [ID: {user[0]}] {user[1]}")

    try:
        user_id = int(input("\nDigite o ID do usuario que deseja remover: "))
    except ValueError:
        print("ID invalido!")
        return

    user = next((u for u in users if u[0] == user_id), None)
    
    if not user:
        print("Usuario nao encontrado!")
        return

    name = user[1]
    confirmacao = (
        input(f"Tem certeza que deseja apagar PERMANENTEMENTE '{name}' (ID: {user_id})? (s/n): ")
        .strip()
        .lower()
    )

    if confirmacao == "s":
        sucesso = db.delete_user(name)

        if sucesso:
            pasta_path = os.path.join(DATASET_DIR, name)
            if os.path.exists(pasta_path):
                shutil.rmtree(pasta_path)
                print(f"Pasta de fotos de '{name}' removida.")
            print(f"Usuario '{name}' deletado com sucesso!")
        else:
            print("Erro ao apagar o usuario do banco de dados.")
    else:
        print("Operacao cancelada.")


def menu():
    db = FaceDatabase()
    while True:
        print("\n=== GERENCIADOR DE CADASTROS (SQLITE) ===")
        print("1. Listar todas as pessoas")
        print("2. Renomear uma pessoa")
        print("3. Apagar uma pessoa")
        print("4. Ver Estatisticas")
        print("5. Sair")

        opcao = input("\nEscolha uma opcao (1-5): ").strip()

        if opcao == "1":
            listar_cadastros(db)
        elif opcao == "2":
            editar_nome(db)
        elif opcao == "3":
            apagar_cadastro(db)
        elif opcao == "4":
            stats = db.get_stats()
            print(f"\nEstatisticas:")
            print(f"  Usuarios: {stats.get('total_users', 0)}")
            print(f"  Encodings: {stats.get('total_encodings', 0)}")
            print(f"  Logs: {stats.get('total_logs', 0)}")
            input("\nPressione [Enter] para continuar...")
        elif opcao == "5":
            print("Saindo...")
            break
        else:
            print("Opcao invalida! Tente novamente.")


if __name__ == "__main__":
    menu()