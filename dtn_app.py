import time, struct, socket, sys, json
import _thread, math, random, subprocess

class DTNagent:

    def __init__(self, probing=1, group='ff02::1', deadint=60, port=9999):
        self.hello_int = probing
        self.ipv6_group = group
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
            fwd_s.sendto(json.dumps([5, res]).encode(), (senderIP, self.port))
            fwd_s.close()

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

    def scheduler(self):
        try:
            _thread.start_new_thread(self.udp_listener, ())
            _thread.start_new_thread(self.tcp_listener, ())
            _thread.start_new_thread(self.recv_input, ())
            _thread.start_new_thread(self.clean_recent, ())
            self.hello_sender() #anchor for the threads
        except:
            print("Scheduling error!")

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
                    elif command[0] == 'news':
                        print(self.news)
                    elif command[0] == 'quit':
                        self.on = False
                        print("Shutting Down")
                    else:
                        print("Invalid command!")

        except EOFError:
            self.on = False
            print("Shutting Down")

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
                else:
                    if x[6] != None:
                        if int(time.time()) > (x[4] + x[6]):
                            self.delMessage(x)
            time.sleep(old)
            i+=1
            i %= 3
            if i == 0:
                self.score = self.score / 2


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



    def hello(self, array):
        nome = array[1]
        score = array[2]
        print("Recebi hello de " + nome + " com score de " + str(score))
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
        print(self.msgtable)
        print(self.deltable)

    #Verifica se já tem a mensagem na msgtable e se sim, atualiza a path. Verifica tb na delTable
    #Se recebeu noticias mais atualizadas que as que tem, apaga as antigas
    #Se recebeu noticias mais antigas que as que ja apagou, ignora
    def have_message(self, array, ip):
        creator = array[1]
        idd = array[2]
        if creator in self.deltable and idd in self.deltable[creator]:
            fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            fwd_s.sendto(json.dumps([6, creator, idd]).encode(), (ip, self.port))
            fwd_s.close()
            return True
        for x in list(self.msgtable):
            if creator == x[1] and idd == x[2]:
                if array[0] != 3:
                    path = array[7]
                    for y in path:
                        if y not in x[7]:
                            x[7].append(y)
                    return True
                else:
                    if creator == x[1] and idd == x[2]:
                        for y in x[5]:
                            if y not in array[5]:
                                x[5].remove(y)
                        return True
        return False

    def delMessage(self, array):
        self.msgtable.remove(array)
        if array[1] in self.deltable:
            self.deltable[array[1]].append(array[2])
            self.score += 1
        else:
            self.deltable[array[1]] = [array[2]]
            self.score += 1

    def sendMessage(self, name, ip):
        fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        array = []
        for x in list(self.msgtable):
            if (x[0] == 1 or x[0] == 2) and x[4] == name:
                fwd_s.sendto(json.dumps(x).encode(), (ip, self.port))
                self.delMessage(x)
            elif x[0] == 3 and name in x[5]:
                if len(x[5]) == 1:
                    self.delMessage(x)
                x[5].remove(name)
                fwd_s.sendto(json.dumps(x).encode(), (ip, self.port))
            elif (x[0] == 1 or x[0] == 2):
                if x[5] != None:
                    array.append([x[4], x[5] + x[6]])
                else:
                    print("Append")
                    array.append([x[4], None])
            elif x[0] == 3:
                for y in x[5]:
                    array.append([y, None])
            if len(array) > 0:
                fwd_s.sendto(json.dumps([4, array]).encode(), (ip, self.port))
        fwd_s.close()

    #Apagar Gets e News
    def delGet(self, array):
        destination = array[4]
        creator = array[1]
        timestamp = array[6]
        for x in list(self.msgtable):
            if destination == x[4] and creator == x[1] and timestamp >= x[6]:
                self.delMessage(x)

    def sendDelNews(self, array, ip):
        msg = [3, self.name, self.id, array[1], array[6], array[7], array[5]]
        self.msgtable.append(msg)
        self.score += 1
        msg[5].pop(len(msg[5])-1)
        if(len(msg[5]) == 0):
            self.delMessage(msg)
        fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        fwd_s.sendto(json.dumps(msg).encode(), (ip, self.port))
        fwd_s.close()
        self.id += 1

    def delNews(self, array):
        self.msgtable.append(array)
        self.score += 1
        for x in list(self.msgtable):
            if x[0] == 2 and x[4] == array[1] and x[1] == array[3] and x[6] <= array[4]:
                self.delMessage(x)
        if len(array[5]) == 0:
            self.delMessage(array)

    def tipo0(self, array, senderIP):
        nome = array[1]
        if nome != self.name:
            self.hello(array)
            self.sendMessage(nome, senderIP)

    def tipo1(self, array, senderIP):
        if array[5] == None or int(time.time()) < (int(array[5]) + int(array[6])): #Verificar se está dentro do timeout
            if not self.have_message(array, senderIP): #Verificar se já recebi esta mensagem por outra pessoa
                array[7].append(self.name)
                self.msgtable.append(array)
                self.score += 1
                target = array[4]
                if target == self.name: #Chegou ao destino
                    tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    tcp_sendnews.connect(('::1', self.port))
                    tcp_sendnews.send(json.dumps(array[8]).encode())
                    tcp_sendnews.close()
                    self.score += 1

    def tipo2(self, array, senderIP):
        if array[5] == None or int(time.time()) - array[6] > array[5]: #Verificar se está dentro do timeout
            if not self.have_message(array, senderIP): #Verificar se já recebi esta mensagem por outra pessoa
                self.delGet(array)
                array[7].append(self.name)
                self.msgtable.append(array)
                self.score += 1
                if array[4] == self.name:
                    self.delMessage(array)
                    self.sendDelNews(array, senderIP)
                    tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    tcp_sendnews.connect(('::1', self.port))
                    tcp_sendnews.send(json.dumps(array[8]).encode())
                    tcp_sendnews.close()

    def tipo3(self, array, senderIP):
        if not self.have_message(array, senderIP):
            self.delNews(array)

    def tipo4(self, array, senderIP):
        self.conhece(array[1], senderIP)

    def tipo5(self, array, senderIP):
        lista = array[1]
        fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        for x in list(self.msgtable):
            if x[0] == 1 or x[0] == 2:
                if x[4] in lista:
                    fwd_s.sendto(json.dumps(x).encode(), (senderIP, self.port))
            elif x[0] == 3:
                for y in x[5]:
                    if y in lista:
                        fwd_s.sendto(json.dumps(x).encode(), (senderIP, self.port))
                        break
        fwd_s.close()

    def tipo6(self, array, senderIP):
        for x in list(self.msgtable):
            if x[2] == array[2] and x[1] == array[1]:
                self.delMessage(x)
                break


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
            if tipo != 0:
                print(array)
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
            elif tipo == 6:
                _thread.start_new_thread(self.tipo6, (array, senderIP, ))





    def get_news(self, data, msg_dest, timeout=0):
        time.sleep(timeout/100)
        if(msg_dest in self.table):
            fwd_s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            fwd_s.sendto(data, ('::1', self.port))
        else:
            tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            tcp_sendnews.connect(('::1', self.port))
            tcp_sendnews.send(json.dumps('').encode())
            tcp_sendnews.close()



    def printhelp(self):
        print()
        print("AER TP2 - DTN distribution 0.1")
        print()
        print("Following commands are available:")
        print("quit - Leave the program")
        print()



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
            if(len(data) == 0):
                client_conn.send(json.dumps(data).encode())
                client_conn.close()
            else:
                Verb= data[0] #GET OR NEWS
                Object = data[1] #DESTINATION
                if Verb == "GET":
                    #Responder a GET com as noticias
                    if data[2] == self.name:
                        if data[3] != None:
                            timeout = data[3] - (int(time.time()) - data[4])
                        else:
                            timeout = data[3]
                        bytes_to_send = json.dumps([2, self.name, self.id, "MSG", Object, timeout, int(time.time()), [], ["NEWS", self.name, Object, self.news]]).encode()
                        self.id += 1
                    #Iniciar pedido de noticias
                    else:
                        client_conn = conn
                        bytes_to_send = json.dumps([1, self.name, self.id, "MSG", Object, data[3], int(time.time()), [], ["GET", self.name, Object, data[3], int(time.time())]]).encode() #ADD MSG header
                        self.id += 1

                    udp_router.connect(('::1', self.port))
                    udp_router.send(bytes_to_send)
                elif Verb == "NEWS":
                    news=data[3]
                    client_conn.send(json.dumps(data).encode())
                    client_conn.close()


if __name__ == '__main__':
    try:
        prob = DTNagent()
        prob.scheduler()
    except KeyboardInterrupt:
        print('Exiting')
