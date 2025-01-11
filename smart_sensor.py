import socket
import threading
import time

# Configurações globais
MULTICAST_GROUP = ('224.1.1.1', 5007)

class SmartSensor:
    def __init__(self, device_id, state):
        self.device_id = device_id
        self.device_type = "temperature_sensor"
        self.state = state
        self.server_socket = None

    def get_local_ip(self):
        return socket.gethostbyname(socket.gethostname())

    def start_device(self):
        # Inicia o servidor TCP primeiro
        tcp_thread = threading.Thread(target=self.start_tcp_server)
        tcp_thread.start()
        # Aguarda a inicialização do server_socket
        while self.server_socket is None:
            time.sleep(0.1)
        # Inicia o multicast
        threading.Thread(target=self.handle_multicast_discovery).start()

    def handle_multicast_discovery(self):
        local_ip = self.get_local_ip()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_sock:
            udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
            while True:
                message = f"{self.device_id},{self.device_type},{self.state},{local_ip},{self.server_socket.getsockname()[1]}"
                udp_sock.sendto(message.encode(), MULTICAST_GROUP)
                time.sleep(10)  # Envia a cada 10 segundos

    def start_tcp_server(self):
        local_ip = self.get_local_ip()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((local_ip, 0))  # Escolha uma porta livre automaticamente
        self.server_socket.listen(5)
        print(f"SmartSensor iniciado no endereço: {self.server_socket.getsockname()}")

        while True:
            conn, _ = self.server_socket.accept()
            threading.Thread(target=self.handle_tcp_connection, args=(conn,)).start()

    def handle_tcp_connection(self, conn):
        try:
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break
                command, *args = data.split(',')
                if command == 'toggle':
                    self.state = 'on' if self.state == 'off' else 'off'
                elif command == 'set_temperature':
                    if args:
                        self.state = f"{args[0]}°C"
                conn.sendall(f"ACK: {self.device_id} updated to {self.state}".encode())
        finally:
            conn.close()

if __name__ == "__main__":
    sensor = SmartSensor("sensor01", "22°C")
    sensor.start_device()
    print("Dispositivo SmartSensor foi iniciado.")
