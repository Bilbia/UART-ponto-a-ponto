#####################################################
# Camada Física da Computação
#Carareto
#11/08/2020
#Aplicação Server
####################################################

from enlace import *
import time
import crcmod
import logging


idServer = 10
EOP = (255).to_bytes(1, 'big') + (170).to_bytes(1, 'big') + (255).to_bytes(1, 'big') + (170).to_bytes(1, 'big')
crc16_func = crcmod.mkCrcFun(0x11021, initCrc=0, xorOut=0xFFFFFFFF)
logging.basicConfig(filename='ServerLog2.txt', filemode='w', format='%(asctime)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S', level=logging.INFO)


def confirmHandshake(header, eopCheck):
    packType = int.from_bytes(header[:1], 'big')
    packIdSensor = int.from_bytes(header[1:2], 'big')
    packIdServer = int.from_bytes(header[2:3], 'big')

    if packType == 1 and EOP == eopCheck and packIdServer == idServer:
        return packIdSensor, True
    else:
        return packIdSensor, False

def buildHandshake(idSensor):
    h0 = (2).to_bytes(1, 'big')
    h1 = idSensor.to_bytes(1, 'big')
    h2 = idServer.to_bytes(1, 'big')
    h3 = (0).to_bytes(1, 'big')
    h4 = (0).to_bytes(1, 'big')
    h5 = (0).to_bytes(1, 'big')
    h6 = (0).to_bytes(1, 'big')
    h7 = (0).to_bytes(1, 'big')
    crc = crc16_func((0).to_bytes(1, 'big')).to_bytes(2, "big")
    header = h0 + h1 + h2 + h3 + h4 + h5 + h6 + h7 + crc
    pack = header + EOP
    return pack

def buildTimeout(idSensor):
    h0 = (5).to_bytes(1, 'big')
    h1 = idSensor.to_bytes(1, 'big')
    h2 = idServer.to_bytes(1, 'big')
    h3 = (0).to_bytes(1, 'big')
    h4 = (0).to_bytes(1, 'big')
    h5 = (0).to_bytes(1, 'big')
    h6 = (0).to_bytes(1, 'big')
    h7 = (0).to_bytes(1, 'big')
    crc = crc16_func(0).to_bytes(2, "big")
    header = h0 + h1 + h2 + h3 + h4 + h5 + h6 + h7 + crc
    pack = header + EOP
    return pack

def confirmBuilder (idSensor, eopCheck, packIdCheck, packIdCounter, crcCheck):
    h0 = (4).to_bytes(1, 'big')
    h1 = idSensor.to_bytes(1, 'big')
    h2 = idServer.to_bytes(1, 'big')
    h3 = (0).to_bytes(1, 'big')
    h4 = (0).to_bytes(1, 'big')
    h5 = (0).to_bytes(1, 'big')
    h6 = packIdCounter.to_bytes(1, 'big')
    h7 = (packIdCounter-1).to_bytes(1, 'big')
    
    if packIdCheck == False or eopCheck == False or crcCheck == False:
        print(packIdCheck)
        print(eopCheck)
        h0 = (6).to_bytes(1, 'big')

    crc = crc16_func(h0).to_bytes(2, "big")
    header = h0 + h1 + h2 + h3 + h4 + h5 + h6 + h7 + crc
    pack = header + EOP
    return pack

        




def main():
    try:
        com2 = enlace('COM5')
        com2.enable() 
        standby = True
        get = True
        packN = 0
        packList = []
        idSensor = 0

        #Handshake
        print("Esperando mensagem de confirmação\n")
        logging.info("Esperando Handshake")
        while standby:
            if not com2.rx.getIsEmpty():
                header, nRx = com2.getData(10)
                eopCheck, nRx = com2.getData(4)
                logging.info("receb / 1 / 14")
                idSensor, confirm = confirmHandshake(header, eopCheck)
                if confirm:
                    print("Ligação estabelecida\n")
                    packN = int.from_bytes(header[3:4], 'big')
                    handshake = buildHandshake(idSensor)
                    com2.sendData(handshake)
                    logging.info("envio / 2 / 14")
                    standby = False
            time.sleep(1)

        
        packIdCounter = 1
        resetTimer = True

        #Getting packages
        print("Esperando pacotes\n-------------------------\n")
        while packIdCounter <= packN:
            if resetTimer:
                timer1 = time.time()
                timer2 = time.time()
            messageEmpty = com2.rx.getIsEmpty()
            if messageEmpty:
                time.sleep(1)
                now = time.time()
                if now - timer2 <= 20:
                    if now - timer1 > 2:
                        resetTimer = False
                    else:
                        # envia mensagem t4????? mas nem chegou mensagem
                        timer1 = time.time()
                        resetTimer = False
                else:
                    standby = True
                    timeout = buildTimeout(idSensor)
                    com2.sendData(timeout)
                    break

            #mensagem recebida
            else:
                print("Recebendo Header...\n")
                header, nRx = com2.getData(10)
                packType = int.from_bytes(header[:1], 'big')
                if packType == 5:
                    print("Timeout com o Client\n")
                    logging.info("receb / 5 / 14")
                    break
                packN = int.from_bytes(header[3:4], 'big')
                packId = int.from_bytes(header[4:5], 'big')
                plSize = int.from_bytes(header[5:6], 'big')
                packLast = int.from_bytes(header[7:8], 'big')
                packCrc = int.from_bytes(header[8:10], 'big')
                print("Recebendo Payload...\n")
                payload, nRx = com2.getData(plSize)
                print("Recebendo EOP...\n")
                packEOP, nRx = com2.getData(4)
                packSize = plSize + 14
                logging.info("receb / 3 / {} / {} / {} / {}".format(packSize, packId, packN, packCrc))
                crcServer = crc16_func(payload)

                crcCheck = True
                packIdCheck = True
                eopCheck = True

                print("Pacote {} de {} recebido\n".format(packId, packN))
                print("Tamanho do pacote: {}\n".format(plSize))
                print(packId)
                print(packIdCounter)

                if packId != packIdCounter:
                    packIdCheck = False
                    print("O pacote {} está fora de ordem\n".format(packId))
                else:
                    print("Ordem dos pacotes correta até agora\n")
                
                if packEOP != EOP:
                    eopCheck = False
                    print("EOP do pacote {} está incorreto\n".format(packId))
                    print("Quantidade de bytes recebidos incompleta\n")

                if packCrc != crcServer:
                    crcCheck = False
                    print("Crc do pacote {} está incorreto\n".format(packId))
                
                
                print("Mandando confirmação para o Client\n-------------------------\n")
                confirmMsg = confirmBuilder(idSensor, eopCheck, packIdCheck, packIdCounter, crcCheck)
                com2.sendData(confirmMsg)
                logging.info("envio / {} / 14".format(int.from_bytes(confirmMsg[:1], 'big')))
                print("Confirmacao mandada\n")
                if packIdCheck == True and eopCheck == True and crcCheck == True:
                    packList.append(payload)
                    packIdCounter += 1
                
                resetTimer = True

        
       
        print("-------------------------\n")
        print("Comunicação encerrada\n")
        print("-------------------------\n")
        com2.disable()  
    except:
        print("ops! :-\\")
        com2.disable()

    #so roda o main quando for executado do terminal ... se for chamado dentro de outro modulo nao roda
if __name__ == "__main__":
    main()
