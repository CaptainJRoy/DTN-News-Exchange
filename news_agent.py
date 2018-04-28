import time, struct, socket, sys, json
import _thread, math, random, subprocess

class NewsAgent:

    def __init__(self, router_port=9999, news_port=9999):
        """

        """
        self.news_bank = ["News1", "News2", "News3"]
        self.router_port = router_port
        self.news_port = news_port
        self.quit = 0
        try:
            self.function = sys.argv[1]
        except:
            print("Problem parsing options")
            self.printhelp()
            sys.exit()

    def run_agent(self):
        try:
            if self.function == "client":
                _thread.start_new_thread(self.run_client, ())
            elif self.function == "server":
                _thread.start_new_thread(self.run_server, ())
            else:
                self.printhelp()
                sys.exit()
            self.run_main()
        except:
            print("Quiting")

    def run_client(self):
        try:
            while True:
                inp = input("Client#>")
                command = inp.split()
                if len(command) > 0:
                    if command[0] == 'help':
                        self.printhelp()
                    elif command[0] == 'quit':
                        self.quit = 1
                        sys.exit()
                    elif len(command) == 2:
                        if command[0] == 'get':
                            self.getnews(command[1])
                    else:
                        print("Invalid command")
                        self.printhelp()

        except EOFError:
            pass

    def run_server(self):
        print("Server started, trying to open socket.")
        news_s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            news_s.bind(('', self.news_port))
        except:
            print ('Problem binding')
            sys.exit()
        news_s.listen(10)
        print("Server running. Waiting for connections on port", self.news_port)
        while True:
            conn, sender = news_s.accept()
            print("Client ",sender[0], " connected with port ", sender[1])
            bytes_to_send = json.dumps([int(time.time()), self.news_bank]).encode()
            bytessent = conn.send(bytes_to_send)
            print ("Sent ", bytessent , "Bytes to client")
            conn.close()
            time.sleep(20)

    def run_main(self):
        print("News agent 0.1, I'm a", self.function)
        while True:
            if self.quit == 1:
                sys.exit()
            time.sleep(1)

    def printhelp(self):
        print()
        print("AER TP1 - News Agent 0.1")
        print()
        print("To run: python3 news_agent [function]:")
        print("server - not int use now")
        print("client - act as a news client")
        print()
        print("To use as client:")
        print("get [node_name] - Get news from the node")
        print("help - show this message")
        print("quit - Exit application")
        print()

    def getnews(self,server):
        print("Server started, trying to open socket.")
        getnews_s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        print("Trying to connect to application layer (adhoc router)")
        getnews_s.connect(('::1', self.router_port))
        print("Resquesting news to server: ", server)
        bytes_to_send = json.dumps(["GET", server, None]).encode()
        getnews_s.send(bytes_to_send)
        news=getnews_s.recv(1024)
        args = json.loads(news.decode())
        getnews_s.close()
        if(args == ""):
            print("Requested node not found")
        else:
            print(args[3])

if __name__ == '__main__':
    try:
        news = NewsAgent()
        news.run_agent()
    except KeyboardInterrupt:
        print('Exiting')
