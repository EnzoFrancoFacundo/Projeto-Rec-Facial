import cv2

# O número 0 seleciona a câmera padrão do seu computador
# Se tiver mais de uma câmera (ex: webcam externa), tente usar 1 ou 2
cap = cv2.VideoCapture(0)

# Verifica se a câmera foi aberta corretamente
if not cap.isOpened():
    print("Erro ao acessar a câmera.")
    exit()

print("Câmera conectada com sucesso! Pressione 'q' na janela para fechar.")

while True:
    # cap.read() lê um quadro (frame) da câmera
    # 'ret' é um booleano (True/False) que indica se o quadro foi capturado com sucesso
    # 'frame' é a imagem capturada naquele instante
    ret, frame = cap.read()

    if not ret:
        print("Não foi possível receber o quadro da câmera. Saindo...")
        break

    # Exibe o frame da câmera na janela
    cv2.imshow('Camera ao Vivo', frame)

    # Espera 1ms por uma tecla. Se a tecla for 'q', o loop é interrompido
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Libera o acesso à câmera e fecha as janelas abertas
cap.release()
cv2.destroyAllWindows()