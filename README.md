Sistema de Reconhecimento Facial em Python
Este projeto consiste em uma aplicação para cadastro, treinamento e reconhecimento facial em tempo real utilizando Python e SQLite.

Pré-requisitos e Dependências

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

Passo 3: Treinamento do Modelo
Processa as imagens capturadas e treina o modelo para reconhecer os perfis cadastrados.

Bash
python treinar.py
Instruções: O script listará os usuários cadastrados no banco de dados. Selecione o perfil desejado para iniciar o processamento dos dados faciais.

Passo 4: Reconhecimento Facial em Tempo Real
Inicia a verificação via câmera utilizando os dados treinados.

Bash
python reconhecer.py
Resultado:

Face reconhecida: Exibe um retângulo verde ao redor do rosto acompanhado do nome cadastrado.

Face não reconhecida: Exibe o rótulo "Desconhecido".