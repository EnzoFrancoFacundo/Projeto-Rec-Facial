import os
import shutil
import pickle

DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings.pickle"


def listar_cadastros():
    if not os.path.exists(DATASET_DIR):
        print("\n❌ Nenhum cadastro encontrado. A pasta 'dataset' ainda não existe.")
        input("\nPressione [Enter] para voltar ao menu...")
        return []

    pessoas = sorted([p for p in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, p))])

    if not pessoas:
        print("\n Nenhuma pessoa cadastrada no momento.")
        input("\nPressione [Enter] para voltar ao menu...")
        return []

    print("\n--- PESSOAS CADASTRADAS ---")
    for i, nome in enumerate(pessoas, 1):
        caminho = os.path.join(DATASET_DIR, nome)
        num_fotos = len(os.listdir(caminho))
        print(f"{i}. {nome} ({num_fotos} fotos)")
    print("---------------------------")
    
    # Ajuste da Opção 1: Agora aguarda o usuário ler antes de limpar a tela ou voltar pro menu
    input("\nPressione [Enter] para voltar ao menu...")
    return pessoas


def editar_nome():
    # Uma versão temporária do listar que não trava com input no meio da edição
    if not os.path.exists(DATASET_DIR):
        print("\n❌ Pasta 'dataset' não encontrada.")
        return
    pessoas = sorted([p for p in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, p))])
    if not pessoas:
        print("\nNenhuma pessoa cadastrada para editar.")
        return

    print("\n--- SELECIONE PARA RENOMEAR ---")
    for i, nome in enumerate(pessoas, 1):
        print(f"{i}. {nome}")
    print("--------------------------------")

    nome_antigo = input("\nDigite o Nome exato da pessoa que deseja renomear: ").strip()
    caminho_antigo = os.path.join(DATASET_DIR, nome_antigo)

    if not os.path.exists(caminho_antigo):
        print(f"❌ [ERRO] O cadastro '{nome_antigo}' não foi encontrado.")
        return

    novo_nome = input(f"Digite o NOVO nome para '{nome_antigo}': ").strip()
    if not novo_nome:
        print("❌ [ERRO] O nome não pode ser vazio.")
        return

    caminho_novo = os.path.join(DATASET_DIR, novo_nome)
    if os.path.exists(caminho_novo):
        print(f"❌ [ERRO] Já existe uma pessoa cadastrada com o nome '{novo_nome}'.")
        return

    os.rename(caminho_antigo, caminho_novo)
    print(f"\nSucesso! '{nome_antigo}' foi alterado para '{novo_nome}'.")
    print("IMPORTANTE: Execute 'python treinar.py' para atualizar as assinaturas faciais.")


def apagar_cadastro():
    if not os.path.exists(DATASET_DIR):
        print("\n❌ Pasta 'dataset' não encontrada.")
        return
    pessoas = sorted([p for p in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, p))])
    if not pessoas:
        print("\n Nenhuma pessoa cadastrada para apagar.")
        return

    print("\n--- SELECIONE PARA APAGAR ---")
    for i, nome in enumerate(pessoas, 1):
        print(f"{i}. {nome}")
    print("------------------------------")

    nome_para_apagar = input("\nDigite o Nome exato da pessoa que deseja APAGAR: ").strip()
    caminho_pasta = os.path.join(DATASET_DIR, nome_para_apagar)

    if not os.path.exists(caminho_pasta):
        print(f"❌ [ERRO] O cadastro '{nome_para_apagar}' não foi encontrado.")
        return

    confirmacao = input(f" Tem certeza que deseja apagar PERMANENTEMENTE '{nome_para_apagar}' e remover seus dados da IA? (s/n): ").strip().lower()
    if confirmacao == 's':
        # 1. Deleta a pasta física de fotos
        shutil.rmtree(caminho_pasta)
        print(f"🗑️ Pasta de fotos de '{nome_para_apagar}' removida.")

        # 2. Abre o encodings.pickle e limpa os dados da memória da IA na mesma hora
        if os.path.exists(ENCODINGS_FILE):
            try:
                with open(ENCODINGS_FILE, "rb") as f:
                    dados = pickle.load(f)

                encodings_antigos = dados["encodings"]
                nomes_antigos = dados["names"]

                # Filtra mantendo apenas quem NÃO for a pessoa apagada
                indices_para_manter = [i for i, n in enumerate(nomes_antigos) if n.lower() != nome_para_apagar.lower()]
                
                encodings_novos = [encodings_antigos[i] for i in indices_para_manter]
                nomes_novos = [nomes_antigos[i] for i in indices_para_manter]

                # Salva o arquivo atualizado sem rastros da pessoa deletada
                dados_atualizados = {"encodings": encodings_novos, "names": nomes_novos}
                with open(ENCODINGS_FILE, "wb") as f:
                    pickle.dump(dados_atualizados, f)
                
                print(f" Assinaturas faciais de '{nome_para_apagar}' removidas com sucesso do '{ENCODINGS_FILE}'.")
            except Exception as e:
                print(f"⚠️ Erro ao atualizar o arquivo pickle: {e}")
        else:
            print("Arquivo 'encodings.pickle' não existia, portanto nenhum dado de IA precisou ser limpo.")
    else:
        print("\n❌ Operação cancelada.")


def menu():
    while True:
        print("\n=== GERENCIADOR DE CADASTROS ===")
        print("1. Listar todas as pessoas")
        print("2. Renomear uma pessoa")
        print("3. Apagar uma pessoa")
        print("4. Sair")

        opcao = input("\nEscolha uma opção (1-4): ").strip()

        if opcao == "1":
            listar_cadastros()
        elif opcao == "2":
            editar_nome()
        elif opcao == "3":
            apagar_cadastro()
        elif opcao == "4":
            print("Saindo do gerenciador...")
            break
        else:
            print("❌ Opção inválida! Tente novamente.")


if __name__ == "__main__":
    menu()
