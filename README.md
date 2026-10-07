# Sistema de Reconhecimento Facial em Python 
Este projeto consiste em uma aplicação para cadastro, treinamento e reconhecimento facial em tempo real utilizando Python e SQLite.

Pré-requisitos e Dependências

(Parte Backend local)

1. Ambiente Python
Versão recomendada: Python 3.12 (compatível com versões anteriores, desde que ofereçam suporte às bibliotecas do projeto).

2. Ferramentas de Compilação (C++)
Algumas dependências do projeto (como dlib ou OpenCV) exigem a compilação de código em C++.

Caso esteja no Windows e enfrente erros durante a instalação das dependências, instale o Visual Studio Build Tools ativando a carga de trabalho "Desenvolvimento para Desktop com C++".

Download do Visual Studio Build Tools

Instalação
Clone o repositório para o seu ambiente local:

Bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DA_PASTA>
Instale os pacotes e dependências necessárias:

Bash
pip install -r requirements.txt
(Nota: Certifique-se de que o nome do arquivo seja requirements.txt com "est").

(Opcional) Teste de Ambiente:
Execute o script de verificação para garantir que as bibliotecas principais foram carregadas corretamente:

Bash
python teste.py
Fluxo de Execução e Uso
Siga a ordem dos passos abaixo para configurar o ambiente e utilizar o sistema:

Passo 1: Inicialização do Banco de Dados
Cria a estrutura de armazenamento SQLite (faces.db) onde serão guardados os cadastros e as referências faciais.

Bash
python database.py
Passo 2: Cadastro de Face
Captura imagens do usuário via webcam para registrar uma nova face.

Bash
python cadastro.py
Instruções:

Informe o seu nome no terminal quando solicitado.

Confirme o início da sessão de fotos na janela que será exibida.

Dica: Varie a posição, a inclinação e a expressão do rosto durante as fotos para aumentar a precisão do reconhecimento.

Passo 3: Reconhecimento Facial em Tempo Real
Inicia a verificação via câmera utilizando os dados treinados.

Bash
python reconhecer.py
Resultado:

Face reconhecida: Exibe um retângulo verde ao redor do rosto acompanhado do nome cadastrado.

Face não reconhecida: Exibe o rótulo "Desconhecido".

(Parte WEB)

# Aplicação Web de Reconhecimento Facial

Uma aplicação web baseada em Flask para deteção e reconhecimento facial utilizando OpenCV e Haar Cascades.

📁 Estrutura do Projeto

web/
├── app.py                             # Lógica principal da aplicação Flask
├── faces.db                           # Base de dados com codificação facial e dados de utilizadores
├── trainer.yml                        # Ficheiro do modelo treinado para reconhecimento facial
├── haarcascade_frontalface_default.xml # Classificador Haar Cascade do OpenCV para deteção de rostos
├── dataset/                           # Diretório com os conjuntos de dados de rostos dos utilizadores
│   └── Enzo/                          # Exemplo de dataset para o utilizador "Enzo"
│       ├── 0.jpg
│       ├── 1.jpg
│       └── ...
├── static/                            # Ficheiros estáticos (estilos, imagens, ícones)
│   └── logo.ico
└── templates/                         # Modelos HTML para as visualizações da aplicação
├── index.html                     # Painel principal / página inicial
└── login.html                     # Página de autenticação de utilizadores

🚀 Funcionalidades

Deteção Facial: Deteta rostos humanos em imagens ou transmissões de vídeo utilizando OpenCV Haar Cascades (haarcascade_frontalface_default.xml).

Modelo de Reconhecimento Facial: Reconhece utilizadores registados através do modelo treinado (trainer.yml).

Gestão de Dataset: Organiza imagens faciais individuais em pastas estruturadas por utilizador dentro de dataset/.

Integração com Base de Dados: Armazena perfis de utilizadores e registos de deteção utilizando SQLite (faces.db).

Painel Web: Interface web interativa construída com Flask e modelos HTML.

🛠️ Pré-requisitos

Certifique-se de que tem o seguinte instalado no seu computador:

Python: 3.8+

pip: Gestor de pacotes do Python

📦 Instalação e Configuração

Clonar ou Transferir o Repositório
Garanta que a estrutura de diretórios corresponde ao esquema apresentado acima.

Navegar para o Diretório do Projeto

cd web

Instalar as Dependências Necessárias
Instale o OpenCV, Flask e as bibliotecas necessárias:

pip install flask opencv-python opencv-contrib-python pillow

🏃 Como Executar

Executar a Aplicação Flask

python app.py

Aceder à Aplicação
Abra o seu navegador e aceda a:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

⚙️ Como Funciona

Recolha de Dados: As imagens dos rostos são armazenadas em dataset/<nome_utilizador>/ (ex.: dataset/Enzo/).

Treino: O treinador facial processa as imagens a partir do diretório dataset/ e atualiza o ficheiro trainer.yml.

Deteção e Reconhecimento: Ao executar o app.py, o OpenCV utiliza o haarcascade_frontalface_default.xml para localizar rostos em tempo real ou em fotos carregadas, cruzando depois os dados com o trainer.yml e a faces.db.
