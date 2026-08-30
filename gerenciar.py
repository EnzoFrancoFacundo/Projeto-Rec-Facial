import os
import shutil
from database import FaceDatabase

DATASET_DIR = "dataset"

<<<<<<< Updated upstream
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
=======
def listar_cadastros():
    db = FaceDatabase()
    # Consulta os dados direto da tabela SQLite 'users'
    usuarios = db.get_all_users()

    if not usuarios:
        print("\n Nenhuma pessoa cadastrada no banco de dados no momento.")
        input("\nPressione [Enter] para voltar ao menu...")
        return []

    print("\n--- PESSOAS CADASTRADAS NO SQLITE ---")
    # O método get_all_users retorna tuplas: (id, name, created_at)
    for i, user in enumerate(usuarios, 1):
        id_usuario, nome, criado_em = user
        
        # Opcional: Ainda verifica se existe uma pasta física correspondente
        caminho_pasta = os.path.join(DATASET_DIR, nome)
        info_fotos = ""
        if os.path.exists(caminho_pasta):
            num_fotos = len(os.listdir(caminho_pasta))
            info_fotos = f" ({num_fotos} fotos em disco)"
            
        print(f"{i}. ID {id_usuario}: {nome}{info_fotos}")
    print("--------------------------------------")
    
    input("\nPressione [Enter] para voltar ao menu...")
    return usuarios


def editar_nome():
    db = FaceDatabase()
    usuarios = db.get_all_users()
    if not usuarios:
        print("\n Nenhuma pessoa cadastrada para editar.")
        return

    print("\n--- SELECIONE PARA RENOMEAR ---")
    for i, user in enumerate(usuarios, 1):
        print(f"{i}. {user[1]}")
    print("--------------------------------")

    nome_antigo = input("\nDigite o Nome exato da pessoa que deseja renomear: ").strip()
    
    # Busca se o usuário realmente existe no banco
    usuario_existente = db.get_user_by_name(nome_antigo)
    if not usuario_existente:
        print(f" ❌ [ERRO] O cadastro '{nome_antigo}' não foi encontrado no banco de dados.")
>>>>>>> Stashed changes
        return
    user = db.get_user_by_id(user_id)
    if not user:
        print("❌ Usuário não encontrado!")
        return
    old_name = user[1]
    novo_nome = input(f"Digite o NOVO nome para '{old_name}': ").strip()
    if not novo_nome:
<<<<<<< Updated upstream
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
=======
        print(" ❌ [ERRO] O nome não pode ser vazio.")
        return

    # Tenta atualizar o nome na tabela users do SQLite
    sucesso = db.update_user_name(nome_antigo, novo_nome)
    if sucesso:
        # Se a pasta física de fotos existir, renomeia ela também para manter a organização
        caminho_antigo = os.path.join(DATASET_DIR, nome_antigo)
        caminho_novo = os.path.join(DATASET_DIR, novo_nome)
        if os.path.exists(caminho_antigo) and not os.path.exists(caminho_novo):
            os.rename(caminho_antigo, caminho_novo)
            print(f" Pasta de fotos atualizada para '{novo_nome}'.")
            
        print(f"\n Sucesso! '{nome_antigo}' foi alterado para '{novo_nome}' no SQLite.")
    else:
        print("[ERRO] Falha ao atualizar. Verifique se o novo nome já pertence a outro usuário.")


def apagar_cadastro():
    db = FaceDatabase()
    usuarios = db.get_all_users()
    if not usuarios:
        print("\n Nenhuma pessoa cadastrada para apagar.")
        return

    print("\n--- SELECIONE PARA APAGAR ---")
    for i, user in enumerate(usuarios, 1):
        print(f"{i}. {user[1]}")
    print("------------------------------")

    nome_para_apagar = input("\nDigite o Nome exato da pessoa que deseja APAGAR: ").strip()

    usuario_existente = db.get_user_by_name(nome_para_apagar)
    if not usuario_existente:
        print(f"[ERRO] O cadastro '{nome_para_apagar}' não foi encontrado no banco de dados.")
        return

    confirmacao = input(f"Tem certeza que deseja apagar PERMANENTEMENTE '{nome_para_apagar}' do banco SQLite? (s/n): ").strip().lower()
    if confirmacao == 's':
        # 1. Remove do banco de dados SQLite (chama o método que corrige o CASCADE)
        sucesso = db.delete_user(nome_para_apagar)
        
        if sucesso:
            print(f" Usuário '{nome_para_apagar}' e assinaturas faciais removidos do SQLite.")
            
            # 2. Deleta a pasta física de fotos para economizar espaço em disco
            caminho_pasta = os.path.join(DATASET_DIR, nome_para_apagar)
            if os.path.exists(caminho_pasta):
                shutil.rmtree(caminho_pasta)
                print(f" Pasta de fotos física removida.")
        else:
            print(" ❌ [ERRO] Falha ao deletar do banco de dados.")
    else:
        print("\n Operação cancelada.")
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
        print("\n=== GERENCIADOR - SQLite ===")
        print("1. Listar pessoas")
        print("2. Renomear pessoa")
        print("3. Apagar pessoa")
        print("4. Estatísticas")
        print("5. Sair")
        opcao = input("\nOpção (1-5): ")
=======
        print("\n=== GERENCIADOR DE CADASTROS (SQLITE) ===")
        print("1. Listar todas as pessoas")
        print("2. Renomear uma pessoa")
        print("3. Apagar uma pessoa")
        print("4. Sair")

        opcao = input("\nEscolha uma opção (1-4): ").strip()

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            print("❌ Opção inválida!")
=======
            print(" ❌ Opção inválida! Tente novamente.")

>>>>>>> Stashed changes

if __name__ == "__main__":
    menu()
