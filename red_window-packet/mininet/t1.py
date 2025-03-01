from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller
from time import sleep
import os
import subprocess

def stop_controller():
    try:
        subprocess.run(['sudo', 'pkill', '-f', 'ovs-testcontroller'], check=True)
        print("Controller stopped.")
    except subprocess.CalledProcessError:
        print("Controller was not running or error while stopping.")

def cleanup_mininet():
    print("Cleaning up Mininet...")
    os.system('sudo mn -c')

class MyTopo(Topo):
    def build(self):
        switch = self.addSwitch('s1')
        num_nodes = 50  # Изменить значение узлов
        for i in range(1, num_nodes + 1):
            sender = self.addHost(f'sender{i}')
            receiver = self.addHost(f'receiver{i}')
            self.addLink(sender, switch, bw=10, delay='50ms')
            self.addLink(receiver, switch, bw=10, delay='50ms')

def start_receivers(net):
    for i in range(1, 21):
        receiver = net.get(f'receiver{i}')
        receiver.cmd('iperf -s -u -i 1 > receiver_log.txt &')

def start_senders(net):
    for i in range(1, 21):
        sender = net.get(f'sender{i}')
        receiver_ip = f'10.0.0.{i + 20}' 
        sender.cmd(f'iperf -c {receiver_ip} -u -b 10M -t 60 > sender_log_{i}.txt &')

def run_experiment():
    stop_controller()  
    cleanup_mininet() 
    topo = MyTopo()
    net = Mininet(topo=topo)
    net.start()  
    start_receivers(net)  
    sleep(2)  
    start_senders(net)  
    sleep(60)  
    net.stop()  
    os.system('cat receiver_log.txt')

if __name__ == '__main__':
    run_experiment()


