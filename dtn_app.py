import time, struct, socket, sys, json
import _thread, math, random, subprocess

class DTNagent:

    def __init__(self, probing=0.2, group='ff02::1', deadint=60, port=9999):
        self.hello_int = probing
        self.ipv6_group = group
        self.historico = {}
        self.msgtable = []
        self.deltable = {}
        self.messageSent = 0
        self.recente = {}
        self.score = 0
        self.id = 0
        self.port = port
        self.name = sys.argv[1]
        self.news = []
        self.on = True

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
        old = 20000
        while self.on:
            for x in self.recente:
                if(int(time.time()) - self.recente[x] > old ):
                    self.recente.pop(x, None)
            time.sleep(old)
            for x in self.msgtable:
                if x[6] != None:
                    if int(time.time()) - (x[6] + x[7]) > 0:
                        self.msgtable.remove(x)



    def remove_dead(self):
        time.sleep(1)
        """arrayDead = []
        for name in self.table:
            if((int(time.time())-self.table[name][2])>(2*self.hello_int) or (name in arrayDead)):
                arrayDead.append(name)
        for name in arrayDead:
            del self.table["hello", self.name, self.msgtable]"""


    def hello_sender(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        ttl_bin = struct.pack('@i', 1)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        limit = 65500
        n = 0
        while self.on:
            #print("Enviei")
            self.remove_dead()
            bytes_to_send = json.dumps([self.name, 0, self.score]).encode()
            s.sendto(bytes_to_send, (addrinfo[4][0], self.port))
            time.sleep(self.hello_int)


    #Fazer isto
    def udp_sender(self, name):
        for x in self.msgtable:
            break;


    def hello(self, array):
        nome = array[1]
        score = array[2]
        #print("Recebi hello de " + nome + " com score de " + str(score))
        self.recente[nome] = int(time.time())
        if nome in self.historico:
            dados = self.historico[nome]
            if int(time.time()) - dados[0][1] < 20000 :
                dados[0][0] += 1
            else:
                if len(dados) == 5:
                    dados.pop(-1)
                    dados.insert(0, [1, int(time.time())])
                else:
                    dados.insert(0, [1, int(time.time())])
        else:
            self.historico[nome] = [[1, int(time.time())]]
        #print(self.historico)
        #print(self.recente)

    #Verifica se já tem a mensagem na msgtable e se sim, atualiza a path. Verifica tb na delTable
    def have_message(self, array):
        if array[4] in self.deltable and array[2] in self.deltable[array[4]]:
            return False
        for x in self.msgtable:
            if array[4] == x[4]:
                if array[2] == x[2]:
                    for y in array[8]:
                        if y not in x[8]:
                            x[8].append(y)
                    return True
        return False

    def delGet(self, array):
        for x in self.msgtable:
            if array[5] == x[4]:
                if array[4] == x[5]:
                    if array[7] > x[7]:
                        self.delTable[x[4]].append(x[2])


    def udp_listener(self):
        addrinfo = socket.getaddrinfo(self.ipv6_group, None)[0]
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Necessário?
        s.bind(('', self.port))
        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        mreq = group_bin + struct.pack('@I', 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

        # Loop
        while self.on:
            data, sender = s.recvfrom(65535)
            array = json.loads(data.decode())
            nome = array[1]
            tipo = array[0]
            senderIP = (str(sender).rsplit('%', 1)[0])[2:] #Retirar apenas o IPv6
            if tipo == 0:
                if nome != self.name:
                    _thread.start_new_thread(self.hello, (array,))
            elif tipo == 1:
                if array[6] == None or int(time.time()) - array[7] > array[6]:
                    #Verificar se já recebi esta mensagem por outra pessoa
                    if not self.have_message(array):
                        self.msgtable.append(array)
                        target = array[5]
                        if target == self.name:
                            tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                            tcp_sendnews.connect(('::1', self.port))
                            tcp_sendnews.send(json.dumps(array[9]).encode())
                            tcp_sendnews.close()
                        else:
                            array[8].append(self.name)
            elif tipo == 2:
                self.delGet(array)
                if array[5] == self.name:
                    tcp_sendnews = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    tcp_sendnews.connect(('::1', self.port))
                    tcp_sendnews.send(json.dumps(array[9]).encode())
                    tcp_sendnews.close()
                else:
                    self.msgtable.append(array)






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
                        bytes_to_send = json.dumps([2, self.name, self.id, "MSG", self.name, Object, timeout, int(time.time()), [], ["NEWS", self.name, Object, self.news]]).encode()
                    #Iniciar pedido de noticias
                    else:
                        client_conn = conn
                        bytes_to_send = json.dumps([1, self.name, self.id, "MSG", self.name, Object, data[3], int(time.time()), [], ["GET", self.name, Object, data[3], int(time.time())]]).encode() #ADD MSG header
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
