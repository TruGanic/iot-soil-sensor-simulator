import json
import time
import random
import requests
import sys
import os
from colorama import init, Fore, Style

# Try importing msvcrt for Windows key detection
try:
    import msvcrt
except ImportError:
    import select
    msvcrt = None

init(autoreset=True)

# --- LOAD CONFIGURATION ---
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(Fore.RED + "❌ Error: config.json not found!")
        sys.exit(1)

config = load_config()

# --- INITIAL SOIL STATE ---
current_state = {
    "Nitrogen": 40.0,
    "Phosphorus": 20.0,
    "Potassium": 20.0,
    "EC": 1.0
}

def get_next_reading(is_spike=False):
    global current_state
    noise = config["sensor_drift_noise"]
    
    if is_spike:
        spike_amt = config["chemical_spike_intensity"]
        current_state['Nitrogen'] += random.uniform(spike_amt, spike_amt + 20)
        current_state['EC'] += random.uniform(1.5, 3.0)
        current_state['Phosphorus'] += random.uniform(2, 5)
        current_state['Potassium'] += random.uniform(2, 5)
        return True 
    else:
        current_state['Nitrogen'] += random.uniform(-noise, noise)
        current_state['Phosphorus'] += random.uniform(-noise, noise)
        current_state['Potassium'] += random.uniform(-noise, noise)
        current_state['EC'] += random.uniform(-0.05, 0.05)
        
        current_state['Nitrogen'] = max(10, current_state['Nitrogen'])
        current_state['Phosphorus'] = max(5, current_state['Phosphorus'])
        current_state['Potassium'] = max(5, current_state['Potassium'])
        current_state['EC'] = max(0.2, current_state['EC'])
        return False

def check_keypress():
    if msvcrt: 
        if msvcrt.kbhit():
            return msvcrt.getch().decode().lower()
    else: 
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    return None

def print_dashboard(payload, response_status, score, spiked,reason=""):
    os.system('cls' if os.name == 'nt' else 'clear') 
    
    print(Fore.CYAN + Style.BRIGHT + "╔════════════════════════════════════════╗")
    print(Fore.CYAN + Style.BRIGHT + "║      🌱 IOT DIGITAL TWIN SENSOR        ║")
    print(Fore.CYAN + Style.BRIGHT + "╚════════════════════════════════════════╝")
    print(f"📡 Target API: {Fore.BLUE}{config['api_url']}")
    print(f"🆔 Sensor ID:  {Fore.YELLOW}{config['sensor_id']} " + Fore.WHITE + "(Matches App Device Pairing)")
    print("-" * 42)
    
    n_color = Fore.RED if spiked else Fore.GREEN
    ec_color = Fore.RED if spiked else Fore.GREEN
    
    print(f"🧪 Nitrogen (N):   {n_color}{payload['Nitrogen']:.2f} ppm")
    print(f"🧪 Phosphorus (P): {Fore.WHITE}{payload['Phosphorus']:.2f} ppm")
    print(f"🧪 Potassium (K):  {Fore.WHITE}{payload['Potassium']:.2f} ppm")
    print(f"⚡ Conductivity:   {ec_color}{payload['EC']:.2f} dS/m")
    print("-" * 42)
    
    # --- SMARTER STATUS LOGIC ---
    if response_status == "CRITICAL ANOMALY" or (response_status and "CRITICAL" in response_status):
        status_color = Fore.RED + Style.BRIGHT + "🚨 CRITICAL ANOMALY"
    elif response_status == "COMPLIANT":
        status_color = Fore.GREEN + "✅ COMPLIANT"
    else:
        # This will properly catch "OFFLINE" or "API ERROR"
        status_color = Fore.YELLOW + f"⚠️ {response_status}"
        
    print(f"☁️  Cloud Status: {status_color}")
    
    # --- SCORE PRINTING LOGIC ---
    if score == "N/A":
        print(f"🏆 Trust Score:  {Fore.YELLOW}N/A")
    else:
        print(f"🏆 Trust Score:  {Fore.WHITE}{score}/100")

    if reason:
        print(f"\n💡 AI Verdict: {Fore.YELLOW}{reason}")
        
    print("\n" + Fore.BLACK + Style.BRIGHT + "Controls: [C] Inject Chemical Spike  |  [Q] Quit")

def main():
    print("Starting sensor...")
    time.sleep(1)
    
    while True:
        key = check_keypress()
        if key == 'q':
            break
        trigger_spike = (key == 'c')
        
        spiked = get_next_reading(trigger_spike)
        
        # --- THE PAYLOAD THAT MATCHES YOUR APP ---
        payload = {
            "sensor_id": config["sensor_id"], # Changed from farm_id
            "Nitrogen": round(current_state['Nitrogen'], 2),
            "Phosphorus": round(current_state['Phosphorus'], 2),
            "Potassium": round(current_state['Potassium'], 2),
            "EC": round(current_state['EC'], 2)
        }

        # 3. Transmit (with Offline Testing Support)
        try:
            response = requests.post(config["api_url"], json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print_dashboard(payload, data.get("status"), data.get("organic_score"), spiked, data.get("reason"))
            else:
                # Server is on, but returned an error (e.g., 404 or 500)
                print_dashboard(payload, f"API ERROR {response.status_code}", 0, spiked)
                
        except requests.exceptions.ConnectionError:
            # SERVER IS OFF: Print the dashboard anyway so we can test the simulator
            print_dashboard(payload, "OFFLINE (No AI Server)", "N/A", spiked)
            
        time.sleep(config["transmission_interval_sec"])
        

if __name__ == "__main__":
    main()
