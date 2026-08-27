import os
import shutil
from database import FaceDatabase

DATASET_DIR = "dataset"

def listar_cadastros(db):
    users = db.get_all_users()
    if not users:
        print("\n❌ Nenhum usuário cadastrado!")
        return
    print("\n👥 USUÁRIOS CADASTRADOS:")
    for user_id, name, created_at in users:
        encodings = db.get_encodings_by_user(user_id)
        print(f"  [{user_id}] {name} - {len(encodings)} encodings")
    input("\nPressione [Enter] para continuar...")

def editar_nome(db):
    users = db.get_all_users()
    if not users:
        print("\n❌ Nenhum usuário cadastrado!")
        return
    print("\n📝 SELECIONE O USUÁRIO:")
    for user_id, name, _ in users:
        print(f"  [{user_id}] {name}")
    try:
        user_id = int(input("\nDigite o ID do usuário: "))
    except ValueError:
        print("❌ ID inválido!")
        return
    user = db.get_user_by_id(user_id)
    if not user:
        print("❌ Usuário não encontrado!")
        return
    old_name = user[1]
    novo_nome = input(f"Digite o NOVO nome para '{old_name}': ").strip()
    if not novo_nome:
        print("❌ Nome não pode ser vazio!")
        return
    if db.update_user_name(old_name, novo_nome):
        old_path = os.path.join(DATASET_DIR, old_name)
        new_path = os.path.join(DATASET_DIR, novo_nome)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
        print(f"✅ Nome alterado para '{novo_nome}'")
    else:
        print("❌ Erro ao renomear")

def apagar_cadastro(db):
    users = db.get_all_users()
    if not users:
        print("\n❌ Nenhum usuário cadastrado!")
        return
    print("\n🗑️ SELECIONE O USUÁRIO:")
    for user_id, name, _ in users:
        print(f"  [{user_id}] {name}")
    try:
        user_id = int(input("\nDigite o ID do usuário: "))
    except ValueError:
        print("❌ ID inválido!")
        return
    user = db.get_user_by_id(user_id)
    if not user:
        print("❌ Usuário não encontrado!")
        return
    name = user[1]
    confirmacao = input(f"⚠️ Apagar PERMANENTEMENTE '{name}'? (s/n): ").strip().lower()
    if confirmacao == 's':
        if db.delete_user(name):
            pasta_path = os.path.join(DATASET_DIR, name)
            if os.path.exists(pasta_path):
                shutil.rmtree(pasta_path)
            print(f"✅ Usuário '{name}' removido!")
        else:
            print("❌ Erro ao remover")
    else:
        print("❌ Cancelado.")

def menu():
    db = FaceDatabase()
    while True:
        print("\n=== GERENCIADOR - SQLite ===")
        print("1. Listar pessoas")
        print("2. Renomear pessoa")
        print("3. Apagar pessoa")
        print("4. Estatísticas")
        print("5. Sair")
        opcao = input("\nOpção (1-5): ")
        if opcao == "1":
            listar_cadastros(db)
        elif opcao == "2":
            editar_nome(db)
        elif opcao == "3":
            apagar_cadastro(db)
        elif opcao == "4":
            stats = db.get_stats()
            print(f"\n📊 Estatísticas:")
            print(f"  Usuários: {stats['total_users']}")
            print(f"  Encodings: {stats['total_encodings']}")
            print(f"  Logs: {stats['total_logs']}")
            input("\nPressione [Enter]...")
        elif opcao == "5":
            print("👋 Saindo...")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    menu()
