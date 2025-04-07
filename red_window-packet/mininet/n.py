from mininet.net import Mininet
from mininet.topo import Topo
from mininet.log import setLogLevel, info
import re
import os
import time
import threading
import matplotlib.pyplot as plt
import numpy as np
import subprocess

def cleanup_mininet():
    info("*** Очистка Mininet\n")
    os.system("sudo mn -c > /dev/null 2>&1")

class MyTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s0 = self.addSwitch('s0')
        self.addLink(h1, s0)
        self.addLink(h2, s0)

def monitor_tc_qdisc(switch, queue_data, drop_data):
    """Сбор данных о очереди и потерях"""
    start_time = time.time()
    prev_dropped = 0  # Храним предыдущее значение дропов

    while time.time() - start_time < 60:
        output = switch.cmd("tc -s -d qdisc show dev s0-eth1")

        #--Для проверки правильности вычисления данных---
        # print("\n[DEBUG] Raw tc output:")
        # print(output)  # Сырые данные для проверки
        #------------------------------------------------

        queue_size = 0
        dropped = 0

        for line in output.split('\n'):
            if 'backlog' in line and 'b' in line:
                backlog_str = line.split()[1].replace('b', '')
                match = re.match(r"(\d+)([KMG]?)", backlog_str)
                if match:
                    num, suffix = match.groups()
                    multiplier = {
                        'K': 1024,
                        'M': 1024**2,
                        'G': 1024**3,
                        '': 1
                    }[suffix]
                    queue_size = int(num) * multiplier

            if 'dropped' in line and 'marked' not in line:
                dropped_str = line.split('dropped ')[1].split(',')[0]
                dropped = int(dropped_str)

        # Считаем разницу с предыдущим замером
        current_drops = dropped - prev_dropped
        prev_dropped = dropped  # Обновляем предыдущее значение

        queue_data.append(queue_size)
        drop_data.append(max(0, current_drops))  # Защита от отрицательных значений
        print(f"Time: {time.time()-start_time:.1f}s | Queue: {queue_size/1024:.1f}KB | Drops: {current_drops}")
        time.sleep(0.2)

def tcp_monitor(host, server_ip, window_data):
    """Сбор данных о TCP окне с точным фильтром"""
    start_time = time.time()
    time.sleep(2)  # Даем время на установку соединения
    
    while time.time() - start_time < 60:
        try:
            # Фильтр по IP сервера и порту 5001 (iperf)
            cmd = f"ss -tin dst {server_ip} dport 5001"
            output = host.cmd(cmd)
            
            if not output:
                time.sleep(0.2)
                continue

            # Ищем строку с cwnd во всех строках вывода
            for line in output.split('\n'):
                if 'cwnd:' in line:
                    cwnd_str = line.split('cwnd:')[1].split()[0]
                    cwnd = int(cwnd_str)
                    window_data.append(cwnd)
                    print(f"Debug: Found cwnd = {cwnd}")  # Отладочный вывод
                    break
            else:
                print("Debug: No cwnd in output")
                
        except Exception as e:
            print(f"Error: {str(e)}")
        
        time.sleep(0.2)  # Частота опроса

def plot_graphs(queue_data, drop_data, window_data):
    """Построение графиков"""
    time_queue = np.arange(len(queue_data)) * 0.2
    time_window = np.arange(len(window_data)) * 0.2

    plt.figure(figsize=(12, 8))

    # График размера очереди
    plt.subplot(311)
    plt.plot(time_queue, queue_data, 'b-', label='Queue Size')
    plt.xlabel('Time (s)')
    plt.ylabel('Bytes')
    plt.title('RED Queue Dynamics')
    plt.grid(True)

    # График отброшенных пакетов
    plt.subplot(312)
    plt.plot(time_queue, drop_data, 'r-', label='Dropped Packets')
    plt.xlabel('Time (s)')
    plt.ylabel('Packets')
    plt.title('Packet Drops')
    plt.grid(True)

    # График TCP окна
    plt.subplot(313)
    plt.plot(time_window, window_data, 'm-', label='TCP Window')
    plt.xlabel('Time (s)')
    plt.ylabel('Packets')
    plt.title('TCP Congestion Window')
    plt.grid(True)

    plt.tight_layout()
    plt.show()

def runMininet():
    cleanup_mininet()  # Очистка перед стартом
    net = Mininet(topo=MyTopo())
    net.start()

    h1 = net.get('h1')
    h2 = net.get('h2')
    s0 = net.get('s0')

    # Проверка наличия ss на хостах
    print("Checking ss utility:")
    print("h1:", h1.cmd("which ss"))
    print("h2:", h2.cmd("which ss"))
    # Настройка RED
    s0.cmd("tc qdisc add dev s0-eth1 root handle 1: htb default 1")
    s0.cmd("tc class add dev s0-eth1 parent 1: classid 1:1 htb rate 100mbit ceil 100mbit")
    s0.cmd("tc qdisc add dev s0-eth1 parent 1:1 handle 2: red limit 500000 min 30000 max 100000 avpkt 1500 burst 73 probability 1.0")
    queue_data = []
    drop_data = []
    window_data = []

    # Запуск мониторинга
    tc_thread = threading.Thread(target=monitor_tc_qdisc, args=(s0, queue_data, drop_data))
    tcp_thread = threading.Thread(target=tcp_monitor, args=(h2, h1.IP(), window_data))
    tc_thread.daemon = True
    tcp_thread.daemon = True

    tc_thread.start()
    tcp_thread.start()

    # Запуск iperf
    h1.cmd('iperf -s -p 5001 &')  # Явно указываем порт
    time.sleep(1)
    h2.cmd(f'iperf -c {h1.IP()} -p 5001 -t 60 -i 0.2 -P 4 -y C > log.csv &')  # TCP-соединение

    time.sleep(60)
    plot_graphs(queue_data, drop_data, window_data)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    runMininet()

