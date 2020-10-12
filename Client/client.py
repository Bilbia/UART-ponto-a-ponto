#####################################################
# Camada Física da Computação
#Carareto
#11/08/2020
#Aplicação Client
####################################################

from enlace import *
import time
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import math
import crcmod
import logging

idSensor = 12
logging.basicConfig(filename='ClientLog2.txt', filemode='w', format='%(asctime)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S', level=logging.INFO)

def buildPackage(packType, content, idServer):

    #Tipos:   1 - Handshake Client
    #         2 - Handshake Server
    #         3 - Dados
    #         4 - Confirmação dos dados Server
    #         5 - Time out
    #         6 - Erro no pacote Server

    # Cria uma lista com todos os payloads:
    payloadBuffer = open(content, 'rb').read()
    packN = math.ceil(len(payloadBuffer)/114) #dividir a imagem em pacotes de 114 bytes  
    packageList = []
    crc16_func = crcmod.mkCrcFun(0x11021, initCrc=0, xorOut=0xFFFFFFFF) #armazena a funcao que faz o bagui

    
    h0 = packType.to_bytes(1, 'big')
    h1 = idSensor.to_bytes(1, 'big')
    h2 = idServer.to_bytes(1, 'big')
    h3 = packN.to_bytes(1, 'big')
    h6 = (0).to_bytes(1, 'big')
    EOP = (255).to_bytes(1, 'big') + (170).to_bytes(1, 'big') + (255).to_bytes(1, 'big') + (170).to_bytes(1, 'big')

    
    # Handshake Client
    # O handshake acontece depois do cliente especificar o arquivo que vai enviar, ent ele já deve ter o número de pacotes
    if packType == 1:
        h4 = (1).to_bytes(1, 'big')
        h5 = (1).to_bytes(1, 'big')
        h7 = (0).to_bytes(1, 'big')
        crc = crc16_func((0).to_bytes(2, "big")).to_bytes(2, "big")
        header = h0 + h1 + h2 + h3 + h4 + h5 + h6 + h7 + crc
        pack = header + EOP
        packageList.append(pack)
        return packageList


    # Dados
    elif packType == 3:
        for packId in range(packN):
            h4 = (packId + 1).to_bytes(1, 'big')
            if packId == packN - 1:
                payloadSize = len(payloadBuffer) % 114
                h5 = (payloadSize).to_bytes(1, 'big')
            else: 
                payloadSize = 114
                h5 = payloadSize.to_bytes(1, 'big')
            h7 = (packId).to_bytes(1, 'big')
            
            payload = payloadBuffer[:payloadSize]
            crc = crc16_func(payload).to_bytes(2, "big")
            payloadBuffer = payloadBuffer[payloadSize:] 
            header = h0 + h1 + h2 + h3 + h4 + h5 + h6 + h7 + crc
            pack = header + payload + EOP
            packageList.append(pack)
            
        return packageList

    #Timeout
    elif packType == 5:
        h4 = (1).to_bytes(1, 'big')
        h5 = (1).to_bytes(1, 'big')
        h7 = (0).to_bytes(1, 'big')
        crc = crc16_func((0).to_bytes(2, "big")).to_bytes(2, "big")

        header = h0 + h1 + h2 + h3 + h4 + h5 + h6 + h7 + crc
        pack = header + EOP
        packageList.append(pack)
        return packageList
            

    
    
def main():
    try:
        com1 = enlace('COM3')
        com1.enable()
        serverResponseEmpty = True
        aliveCheck = True
        serverOk = False
        packN = 0
        packCounter = 1
        

        # -------------------------- HANDSHAKE --------------------------

        # Pede para o usuário selecionar uma imagem para ser transmitida
        print('\nPor favor escolha um arquivo:\n')
        Tk().withdraw()
        content = askopenfilename()
        print("Arquivo selecionado: {}\n".format(content))
        logging.info("Arquivo selecionado: {}".format(content))

        while aliveCheck:
            print("Checando status do server\n")
            handshake = buildPackage(1, content, 10)[0]
            packN = int.from_bytes(handshake[3:4], 'big')
            com1.sendData(handshake)
            logging.info("envio / 1 / 14")
            print("Esperando resposta do server\n")
            time.sleep(5)
            serverResponseEmpty = com1.rx.getIsEmpty()
            if serverResponseEmpty == True:
                retry = str(input("Servidor inativo. Tentar novamente? S/N: "))
                if retry == 'N' or retry == 'n':
                    aliveCheck = False
                    print("\nAbortando processo\n")
                    break
                else:
                    print("\nTentando novamente\n")
                    continue
            else:
                print("Servidor ativo\n-----------------------------------\n")
                headshake, nRx = com1.getData(14)
                logging.info("receb / 2 / 14")
                aliveCheck = False
                serverOk = True
        
        

        # Só procede para o resto do código se o servidor estiver funcionando
        if serverOk:
            packs = buildPackage(3, content, 10)
            resetTimer = True
            packId = packCounter-1
            while packCounter <= packN:
                print("Mandando pacote {} de {}\n".format(packCounter, packN))
                packSize = len(packs[packId])
                crc = int.from_bytes(packs[packId][8:10], 'big')
                com1.sendData(packs[packId])
                if packId == 6:
                    time.sleep(10)
                logging.info("envio / 3 / {} / {} / {} / {}".format(packSize, packCounter, packN, crc))
                
                if resetTimer:
                    timer1 = time.time()
                    timer2 = time.time()
                print("Esperando confirmação de envio\n")

                serverResponseEmpty = com1.rx.getIsEmpty()
                while serverResponseEmpty:
                    now = time.time()
                    if now - timer1 > 5:
                        timer1 = time.time()
                    if now - timer2 > 20:
                        timeout = buildPackage(5, content, 10)
                        com1.sendData(timeout[0])
                        print("Timeout na conexão com o Server\n") 
                        print("Encerrando comunicação\n")
                        logging.info("envio / 5 / 14")
                        packCounter = packN + 1
                        break
                    serverResponseEmpty = com1.rx.getIsEmpty()
                else:
                    header, nRx = com1.getData(10)
                    eopServer, nRx = com1.getData(4)
                    packType = int.from_bytes(header[:1], 'big')
                    logging.info("receb / {} / 14".format(packType))
                    if packType == 6:
                        print("packu 6")
                        packEsperado = int.from_bytes(header[6:7], 'big') 
                        for index in range(len(packs)):
                            if int.from_bytes(packs[index][4:5], 'big') == packEsperado:
                                packId = index
                                print("mandando o {} certo agora".format(int.from_bytes(packs[index][4:5], 'big')))
                        resetTimer = True
                    else:
                        print("Pacote {} recebido sem problemas\n".format(packCounter))
                        packCounter += 1
                        packId = packCounter - 1
                        resetTimer = True

    
        
        print("-------------------------")
        print("Comunicação encerrada")
        print("-------------------------")
        com1.disable()
    except:
        print("ops! :-\\")
        com1.disable()

    #so roda o main quando for executado do terminal ... se for chamado dentro de outro modulo nao roda
if __name__ == "__main__":
    main()
    