import time, struct, socket, sys, json
import _thread, math, random, subprocess

class DTNagent:

    """
        @self.hello_int - intervalo de tempo entre envio de pacotes hello
        @self.dead_interval - intervalo de tempo ate considerar um no desconectado
        @self.ipv6_group - grupo ipv6 do equipamento que executa o programa
        @self.hello - dicionario de vizinhos, sendo a key o seu nome, contendo o ip e o rtt desde o nodo até ao vizinho como value
        @self.port - porta para comunicar o protocolo hello
        @self.name - nome do nodo
        @self.gets - noticias que espera receber
        @self.historico - 5 vezes que se cruzou com os nodos, com um espaço de 20 segundos (para efeitos de demonstração)
        @self.msgtable - tabela de mensagens a transmitir
        @self.deltable - tabela de mensagens apagadas
        @self.recente - os nodos com quem se cruzou recentemente (20 s para demonstração), e o número de segundos que esteve em contacto
        @self.score - aspeto aleatório para transmissão de pacotes. Atualizado dependendo da atividade do nodo
        @self.id - Identificador do próximo pacote a enviar
        @self.news - noticias do nodo
        @self.on - usado para terminar a atividade
    """
    def __init__(self, probing=1, group='ff02::1', deadint=60, port=9999):
        self.hello_int = probing
        self.ipv6_group = group
        self.gets = []
        self.historico = {}
        self.msgtable = []
        self.deltable = {}
        self.recente = {}
        self.score = 0
        self.id = 0
        self.port = port
        self.name = sys.argv[1]
        self.news = []
        self.on = True

    """
        Função que cria um array com o nome dos nodos, aos quais este nodo consegue
        entregar as mensagens antes do timeout acabarself.
        É assim adicionado ao array se comunicou recentemente com o nodo (está no array recente)
        ou se a função calc_desvio aplicado aos valores do historico com o nodo, devolve um tempo de modo
        a que dê para enviar e devolver uma mensagem com esse tempo.
    """
    def conhece(self, array, senderIP):
        res = []
        for x in array:
            name = x[0]
            timeStamp = x[1]
            if name in list(self.recente):
                rec = self.recente[name]
                if int(time.time()) - int(rec[1]) < 20 and int(rec[0]) > 5:
                    res.append(name)
                elif name in list(self.historico):
                    hist = self.historico[name]
                    calc = self.calc_desvio(hist)
                    if calc != None:
                        if timeStamp != None:
                            if int(time.time()) + 2*calc <= timeStamp:
                                res.append(name)
                        else:
                            res.append(name)

        if len(res) > 0:
            fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            fwd_s.sendto(json.dumps([5, self.name, res]).encode(), (senderIP, self.port))
            fwd_s.close()

    """
        Calcula a diferença média entre os valores, supondo que estes
        estão ordenados.
    """
    def calc_desvio(self, valores):
        l = len(valores)
        i = 1
        soma = 0
        while i < l:
            soma += valores[i] - valores[i-1]
            i += 1
        if soma == 0:
            return None
        return soma / (l-1)

    """
        Função que executa as funções:
        - Que escuta por pacotes UDP
        - Que escuta por pacotes TCP
        - Que escuta por input do utilizador
        - Que limpa os registos antigos em todos os registos
        - Que envia os pacotes hello
        São todas executadas em série, exceto a função que envia os pacotes hello
        para melhorar a eficiência
    """
    def scheduler(self):
        try:
            _thread.start_new_thread(self.udp_listener, ())
            _thread.start_new_thread(self.tcp_listener, ())
            _thread.start_new_thread(self.recv_input, ())
            _thread.start_new_thread(self.clean_recent, ())
            self.hello_sender() #anchor for the threads
        except:
            print("Scheduling error!")

    """
    Imprime todas as funcionalidades da aplicação
    """
    def printhelp(self):
        print()
        print("AER TP1 - News Agent 0.1")
        print()
        print("To use as client:")
        print("get [node_name] [timeout] [s (seconds) /d (days) /w (week) /y (year)] - Get news from the node. ")
        print("set [news] - Colocar noticias no nodo")
        print("news - Ler as noticias do nodo")
        print("help - show this message")
        print("quit - Exit application")
        print()

    """
    Input que poderá inserir o utilizador:
    Explicado na função "printhelp"
    """
    def recv_input(self):
        try:
            while self.on:
                inp = input(self.name+ "#>")
                command = inp.split()
                if len(command) > 0:
                    if command[0] == 'help':
                        self.printhelp()
                    elif len(command)==1 and command[0] == 'clear':
                        print("\033c")
                    elif command[0] == 'set':
                        self.news.append(" ".join(command[1:]))
                    elif command[0] == 'historico':
                        print("#####################")
                        print(self.historico)
                        print("#####################")
                    elif command[0] == 'recente':
                        print("#####################")
                        print(self.recente)
                        print("#####################")
                    elif command[0] == "msgtable":
                        print("#####################")
                        for x in list(self.msgtable):
                            path = ", ".join(x[7])
                            print("-----------------------------")
                            print("Tipo " + str(str(x[0])) + " ID: " + str(x[2]) + ". De " + str(x[1]) + " -> " + str(x[4]) + ". Timeout " + str(x[5]) + " s. Path: " + path + ". Score" + str(x[8]))
                            print("-----------------------------")
                        print("#####################")
                    elif command[0] == "deltable":
                        print(self.deltable)
                    elif command[0] == "score":
                        print(self.score)
                    elif command[0] == 'news':
                        print(self.news)
                    elif command[0] == 'get':
                        tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                        tcp_sendnews.connect(('::1', self.port))
                        if len(command) == 2:
                            tcp_sendnews.send(json.dumps(["GET", None, command[1], None]).encode())
                        else:
                            if command[3] == "s":
                                tcp_sendnews.send(json.dumps(["GET", None, command[1], int(command[2])]).encode())
                            elif command[3] == "d":
                                tcp_sendnews.send(json.dumps(["GET", None, command[1], int(command[2]) * 86400 ]).encode())
                            elif command[3] == "w":
                                tcp_sendnews.send(json.dumps(["GET", None, command[1], int(command[2]) * 86400 * 7]).encode())
                            elif command[3] == "y":
                                tcp_sendnews.send(json.dumps(["GET", None, command[1], int(command[2]) * 86400 * 365]).encode())
                            else:
                                self.printhelp()
                        tcp_sendnews.close()
                    elif command[0] == 'quit':
                        self.on = False
                        print("Shutting Down")
                    else:
                        print("Invalid command!")
        except EOFError:
            self.on = False
            print("Shutting Down")

    """
    Função que limpa todos os registos nas tabelas:
    @self.recent, limpando todos os nodos que realizaram contacto à mais de 20 s
    @self.msgtable, limpando todas mensagens cujo timeout esteja expirado
    """
    def clean_recent(self):
        old = 20
        i = 0
        while self.on:
            for x in list(self.recente):
                if(int(time.time()) - self.recente[x][1] > old ):
                    self.recente.pop(x, None)
            for x in list(self.msgtable):
                if x[0] == 1 or x[0] == 2:
                    if x[5] != None:
                        if int(time.time()) > (int(x[5]) + int(x[6])):
                            self.delMessage(x)
                elif x[0] == 3 and len(x[5]) == 0:
                    self.delMessage(x)
            time.sleep(old)
            i+=1
            i %= 3
            if i == 0:
                self.score = self.score / 2
                for x in list(self.recente):
                    x[9] = x[9] / 2

    """
        Envia os pacotes hello periódicamente, dependendo da variável "self.hello_int".
        Envia o seu nome e o seu score no pacote.
    """
    def hello_sender(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        ttl_bin = struct.pack('@i', 1)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        limit = 65500
        n = 0
        while self.on:
            bytes_to_send = json.dumps([0, self.name, self.score]).encode()
            s.sendto(bytes_to_send, (addrinfo[4][0], self.port))
            time.sleep(self.hello_int)


    """
        Função que a dado um PDU "hello", atualiza os registos do próprio nodo
        adicionando aos registos recentes se ainda não estiver no array. Se estiver
        atualiza o timestamp e incrementa o número de segundos em contacto.
        Adiciona também ao histórico o timestamp, caso o último timestamp seja a mais de
        20 s (para efeitos de demonstração).
    """
    def hello(self, array):
        nome = array[1]
        score = array[2]
        if nome not in self.recente:
            self.score +=1
            self.recente[nome] = [1, int(time.time())]
        else:
            x = self.recente[nome]
            self.recente[nome] = [x[0]+1, int(time.time())]
        if nome in self.historico:
            dados = self.historico[nome]
            if int(time.time()) - dados[0] > 20 :
                if len(dados) == 5:
                    dados.pop(-1)
                    dados.insert(0, int(time.time()))
                else:
                    dados.insert(0, int(time.time()))
        else:
            self.historico[nome] = [int(time.time())]
        print("MsgTable")
        print(self.msgtable)
        print("DelTable")
        print(self.deltable)

    """
    Verifica se já tem a mensagem a receber. Verifica inicialmente se faz parte das mensagens
    eliminadas. Caso faça, envia uma pensagem "delete", do tipo 3, para o nodo que enviou o pacote,
    para notificar para apagar a mensagem que enviou, porque esta já foi tratada.
    Verifica de seguida se já faz parte da sua lista de mensagens a transmitir. Verifica se o
    criador do pacote e o idd coincidem com algum outro pacote na sua lista, e caso coincida e seja um
    pacote "delete", do tipo 3, atualiza os nodos que já foram apagados por outros nodos.
    Retorna False caso não encontre
    """
    def have_message(self, array, ip):
        creator = array[1]
        idd = array[2]
        if creator in self.deltable and idd in self.deltable[creator]:
            fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            if array[0] == 3:
                timeout = array[7]
            else:
                timeout = array[6]
            fwd_s.sendto(json.dumps([3, self.name, self.id, creator, idd, [], [creator], timeout]).encode(), (ip, self.port))
            self.id += 1
            fwd_s.close()
            return True
        for x in list(self.msgtable):
            if creator == x[1] and idd == x[2]:
                if array[0] == 3:
                    for y in x[5]:
                        if y not in array[5]:
                            x[5].remove(y)
                            x[6].append(y)
                return True
        return False

    """
    Apaga a mensagem da self.msgtable, e adiciona à self.table
    """
    def delMessage(self, array):
        self.msgtable.remove(array)
        if array[1] in self.deltable:
            self.deltable[array[1]].append(array[2])
            self.score += 1
        else:
            self.deltable[array[1]] = [array[2]]
            self.score += 1

    """
    Verifica consoante o nome dado, se existe alguma mensagem para lhe enviar.
    Verifica para todas as mensagens da self.msgtable se alguma mensagem tem como
    destino o nome dado como argumento, caso a mensagem a ser testada seja um "GET" ou "NEWS",
    ou verifica se o nome dado como argumento está no caminho da mensagem "delete".
    Caso não se verifique nenhum dos casos, é adicionado o destino da mensagem a ser testada,
    para um array, para perguntar ao nodo para quem vai enviar a mensagem, se conhece
    os nomes que este não conhece.
    """
    def sendMessage(self, name, ip, score):
        fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        array = []
        for x in list(self.msgtable):
            if (x[0] == 1 or x[0] == 2) and x[4] == name and name not in x[7]:
                fwd_s.sendto(json.dumps(x).encode(), (ip, self.port))
            elif (x[0] == 1 or x[0] == 2) and name not in x[7] and score > self.score and score > x[9]:
                x[9] = score
                fwd_s.sendto(json.dumps(x).encode(), (ip, self.port))
            elif x[0] == 3 and (name in x[5] or name in x[6]):
                if name in x[5]:
                    x[5].remove(name)
                    x[6].append(name)
                    if len(x[5]) == 0:
                        self.delMessage(x)
                fwd_s.sendto(json.dumps(x).encode(), (ip, self.port))
            elif (x[0] == 1 or x[0] == 2):
                if name not in x[7]:
                    if x[5] != None:
                        array.append([x[4], x[5] + x[6]])
                    else:
                        array.append([x[4], None])
            if len(array) > 0:
                fwd_s.sendto(json.dumps([4, array]).encode(), (ip, self.port))
        fwd_s.close()

    """
    Apaga os gets e/ou as noticias, dependendo da noticia que receber. Verifica se o criador
    e o destino do pedido de noticia é igual, e verifica se as noticias são mais atualizadas
    que as que tenha na sua self.msgtable, apagando as antigas.
    """
    def delGet(self, array):
        res = False
        destination = array[4]
        creator = array[1]
        timestamp = array[6]
        for x in list(self.msgtable):
            if destination == x[1] and creator == x[4] and timestamp >= x[6] and x[0] == 1:
                self.delMessage(x)
                res = True
            elif x[0] == 2 and destination == x[4] and creator == x[1] and timestamp >= x[6]:
                self.delMessage(x)
        return res

    """
        Enviada uma mensagem de "delete", que irá percorrer o caminho do pacote "GET" ou "NEWS"
        dado como argumento, apagando estes pacotes da self.msgtable desses nodos. Atualiza
        os nodos já vizitados, e mantêm o timeout do pacote "GET" ou "NEWS", parando de percorrer
        o caminho após o timeout expirar. É enviado ao ip dado como argumento, ip correspondente
        ao último nodo que enviou o pacote "GET" ou "NEWS" para o destino.
    """
    def sendDelMsg(self, array, ip):
        if array[5] != None:
            timeout = array[5] + array[6]
        else:
            timeout = None
        msg = [3, self.name, self.id, array[1], array[2], array[7], [], timeout]
        self.id += 1
        self.msgtable.append(msg)
        self.score += 1
        msg[6].append(msg[5].pop(len(msg[5])-1))
        msg[6].append(msg[5].pop(len(msg[5])-1))
        if(len(msg[5]) == 0):
            self.delMessage(msg)
        fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        fwd_s.sendto(json.dumps(msg).encode(), (ip, self.port))
        fwd_s.close()

    """
    Dado um pacote "delete", apaga as mensagens correspondentes. Apaga também
    o pacote "delete" caso não contenha mais nenhum nodo a percorrer
    """
    def delMsgs(self, array):
        self.msgtable.append(array)
        for x in list(self.msgtable):
            if (x[0] == 1 or x[0] == 2) and x[1] == array[3] and x[2] == array[4]:
                self.delMessage(x)
                self.score += 1
                break
            elif x[0] == 3 and array[3] == x[1] and array[4] == x[2]:
                self.delMessage(x)
        if len(array[5]) == 0:
            self.delMessage(array)

    """
    Função invocada sempre que um pacote "hello" for recebido.
    São atualizados os registos, e enviadas as mensagens que forem destinadas a esse
    nodo.
    """
    def tipo0(self, array, senderIP):
        nome = array[1]
        if nome != self.name:
            self.hello(array)
            self.sendMessage(nome, senderIP, array[2])

    """
    Função invocada sempre que um pacote "GET" for recebido.
    Verifica se o timeout do pacote já expirou, ou se já recebeu esse pacote.
    Caso contrário, é adicionado o nome do próprio nodo ao caminho percorrido
    por esse pacote, guardando esse mesmo na self.msgtable. É atualizado o score
    a cada mensagem nova recebida e se for o destino do pacote. Caso este seja o destino do pacote "GET",
    são solicitadas as noticias desse nodo, e enviada uma mensagem "delete" a percorrer o caminho guardado
    no pacote "GET" recebido. É apagado também o pacote "GET" recebido, guardando-o na self.deltable
    """
    def tipo1(self, array, senderIP):
        if array[5] == None or int(time.time()) < (int(array[5]) + int(array[6])): #Verificar se está dentro do timeout
            if not self.have_message(array, senderIP): #Verificar se já recebi esta mensagem por outra pessoa
                array[7].append(self.name)
                self.msgtable.append(array)
                self.score += 1
                target = array[4]
                if target == self.name: #Chegou ao destino
                    self.delMessage(array)
                    self.sendDelMsg(array, senderIP)
                    tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    tcp_sendnews.connect(('::1', self.port))
                    tcp_sendnews.send(json.dumps(array[8]).encode())
                    tcp_sendnews.close()
                    self.score += 1

    """
    Função invocada sempre que um pacote "NEWS" for recebido
    Verifica se o timeout do pacote já expirou, ou se já recebeu esse pacote.
    Caso contrário, é adicionado o seu nome ao caminho já percorrido pelo pacote.
    Caso este seja o nodo destino, são enviadas as noticias para a aplicação TCP, caso
    esteja à espera de receber a noticia. Caso não esteja, é descartada.
    Caso seja o nodo destino, é apagada a noticia, é enviada uma mensagem "delete", que irá
    percorrer o caminho do pacote "NEWS".
    O score é atualizado sempre que receber um pacote "NEWS" novo, e caso este seja o nodo destino.
    """
    def tipo2(self, array, senderIP):
        if array[5] == None or int(time.time()) - array[6] > array[5]: #Verificar se está dentro do timeout
            if not self.have_message(array, senderIP): #Verificar se já recebi esta mensagem por outra pessoa
                array[7].append(self.name)
                self.msgtable.append(array)
                self.score += 1
                if array[4] == self.name:
                    self.delMessage(array)
                    self.sendDelMsg(array, senderIP)
                    if array[1] in self.gets:
                        tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                        tcp_sendnews.connect(('::1', self.port))
                        tcp_sendnews.send(json.dumps(array[8]).encode())
                        tcp_sendnews.close()
                        self.score += 1
                        for x in list(self.gets):
                            if x == array[1]:
                                self.gets.remove(x)

    """
    Função invocada sempre que um pacote "delete" for recebido
    É verificado se não recebeu a mensagem, e caso não o tenha, são apagadas
    as mensagens, de acordo com o pacote recebido.
    """
    def tipo3(self, array, senderIP):
        if not self.have_message(array, senderIP):
            self.delMsgs(array)

    """
    Função invocada sempre que um pacote "conhece" for recebido
    Verifica quais os nodos que este conhece, e que chega antes do timeout expirar
    """
    def tipo4(self, array, senderIP):
        self.conhece(array[1], senderIP)

    """
    Função invocada sempre que um pacote "conheco" for recebido
    São enviadas as mensagens que tenham como destino um dos nodos conhecido pelo
    nodo que enviou o pacote "conheco"
    """
    def tipo5(self, array, senderIP):
        lista = array[2]
        name = array[1]
        fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        for x in list(self.msgtable):
            if x[0] == 1 or x[0] == 2:
                if x[4] in lista:
                    if name not in x[7]:
                        fwd_s.sendto(json.dumps(x).encode(), (senderIP, self.port))
                        if name not in x[7]:
                            x[7].append(name)
        fwd_s.close()

    """
    Função que escuta todos os pacotes UDP. É escutado todos os pacotes
    enviados em multicast para o grupo ipv6 self.ipv6_group. É extraido o PDU
    dos pacotes, através de funções json, e extraido o IP do nodo que enviou o pacote.
    É tratado de cada pacote dependendo do seu tipo (primeiro inteiro de cada PDU).
    0 - pacote hello
    1 - pacote GET
    2 - pacote NEWS
    3 - pacote delete
    4 - pacote conhece
    5 - pacote conheco
    """
    def udp_listener(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        mreq = group_bin + struct.pack('@I', 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        # Loop
        while self.on:
            data, sender = s.recvfrom(65535)
            array = json.loads(data.decode())
            tipo = array[0]
            senderIP = (str(sender).rsplit('%', 1)[0])[2:] #Retirar apenas o IPv6
            if tipo == 0:
                _thread.start_new_thread(self.tipo0, (array, senderIP, ))
            elif tipo == 1:
                _thread.start_new_thread(self.tipo1, (array, senderIP, ))
            elif tipo == 2:
                _thread.start_new_thread(self.tipo2, (array, senderIP, ))
            elif tipo == 3:
                _thread.start_new_thread(self.tipo3, (array, senderIP, ))
            elif tipo == 4:
                _thread.start_new_thread(self.tipo4, (array, senderIP, ))
            elif tipo == 5:
                _thread.start_new_thread(self.tipo5, (array, senderIP, ))

    """
    Função que simula a parte aplicacional.
    Escuta por pacotes TCP. Caso o pacote recebido seja um GET, sem nodo
    criador, é criado um pacote "GET" com o nodo destino e timeout enviados como argumento.
    É também adicionado à variável self.gets, o nodo destino, notificando que está à espera de uma
    noticia daquele nodo.
    Caso receba um pacote "GET", é criado um pacote "NEWS", com as noticias deste nodo.
    Caso receba um pacote "NEWS", são imprimidas as noticias.
    """
    def tcp_listener(self):
        tcp_r = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        udp_router = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        try:
            tcp_r.bind(('', self.port))
        except:
            print ('Problem binding TCP listener. You killed an open tcp socket, wait until you restart again.')
            sys.exit()
        tcp_r.listen(1)

        while self.on:
            conn, sender = tcp_r.accept() #locks until we get something
            data = json.loads(conn.recv(1024).decode())
            Verb= data[0] #GET OR NEWS
            if Verb == "GET":
                #Responder a GET com as noticias
                if data[1] != None:
                    if data[3] != None:
                        timeout = data[3] - (int(time.time()) - data[4])
                    else:
                        timeout = data[3]
                    bytes_to_send = json.dumps([2, self.name, self.id, "MSG", data[1], timeout, int(time.time()), [], ["NEWS", self.name, data[1], self.news], 0]).encode()
                    self.id += 1
                #Iniciar pedido de noticias
                else:
                    bytes_to_send = json.dumps([1, self.name, self.id, "MSG", data[2], data[3], int(time.time()), [], ["GET", self.name, data[2], data[3], int(time.time())], 0]).encode() #ADD MSG header
                    self.gets.append(data[2])
                    self.id += 1
                udp_router.connect(('::1', self.port))
                udp_router.send(bytes_to_send)
            elif Verb == "NEWS":
                news=data[3]
                noticias = ". ".join(news)
                print("######################################")
                print("Noticias de " + data[1] + " -> " + noticias)
                print("######################################")


if __name__ == '__main__':
    try:
        prob = DTNagent()
        prob.scheduler()
    except KeyboardInterrupt:
        print('Exiting')
