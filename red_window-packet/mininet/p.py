import matplotlib.pyplot as plt
import numpy as np

time = np.linspace(0, 30, 100)  
window_size = np.clip(np.random.randint(0, 50, size=100), 0, 40) 

packet_loss = np.random.randint(0, 10, size=100)  

plt.figure(figsize=(14, 6))

plt.subplot(1, 2, 1)
plt.plot(time, window_size, color='blue', marker='o', linestyle='-', label='Window Size (packets)')
plt.xlim(0, 30)
plt.ylim(0, 40)
plt.title('Window Size Over Time')
plt.xlabel('Time (seconds)')
plt.ylabel('Window Size (packets)')
plt.grid(True)
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(time, packet_loss, color='red', marker='x', linestyle='-', label='Packet Loss')
plt.xlim(0, 30)
plt.ylim(0, 10)  
plt.title('Packet Loss Over Time')
plt.xlabel('Time (seconds)')
plt.ylabel('Packet Loss (count)')
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.show()

