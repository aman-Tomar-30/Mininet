import subprocess
import time
import re
from collections import defaultdict

"""
This script collects:

1. MAC Table Entries
2. Flood Pressure
3. Port Traffic
4. Entry Age
5. New MAC Rate
"""

# =========================
# CONFIGURATION
# =========================

SWITCHES = subprocess.check_output(["ovs-vsctl", "list-br"], text=True).split()   #gives list of switches
#print(SWITCHES)
INTERVAL = 5              # seconds

# Estimated limits (customize according to topology)
MAX_MAC_CAPACITY = 200
MAX_FLOOD_RATE = 10000
MAX_BANDWIDTH = 1000000000   # 1 Gbps
MAX_ENTRY_AGE = 300          # seconds
MAX_MAC_RATE = 20

# =========================
# GLOBAL STATE
# =========================

previous_mac_set = set()
previous_port_stats = {}

# =========================
# HELPER FUNCTIONS - which run commands on terminal
# =========================

def run_cmd(cmd):
    """Run shell command"""
    result = subprocess.check_output(cmd, shell=True, text=True)
    return result.strip()


# =========================================================
# 1. MAC TABLE ENTRIES
# =========================================================

def get_mac_table_entries(sw):

    try:
        output = run_cmd(f"ovs-appctl fdb/show {sw}")

        mac_entries = []

        for line in output.splitlines():

            # Example:
            # port VLAN MAC                 Age
            # 1    1     00:00:00:00:00:01 12

            match = re.search(
                r"(\d+)\s+(\d+)\s+([0-9a-f:]{17})\s+(\d+)",
                line,
                re.IGNORECASE
            )

            if match:

                port = match.group(1)
                vlan = match.group(2)
                mac = match.group(3)
                age = int(match.group(4))

                mac_entries.append({
                    "vlan": vlan,
                    "mac": mac,
                    "port": port,
                    "age": age
                })

        return mac_entries

    except Exception as e:
        print(f"[ERROR] MAC table fetch failed: {e}")
        return []


# =========================================================
# 2. FLOOD PRESSURE
# =========================================================

def get_flood_pressure(sw):
    """
    Estimate flooding using OpenFlow flow stats

    Flood packets are usually NORMAL/FLOOD actions.
    """

    try:
        output = run_cmd(f"ovs-ofctl dump-flows {sw}")

        flood_packets = 0

        for line in output.splitlines():

            if "FLOOD" in line or "NORMAL" in line:

                match = re.search(r"n_packets=(\d+)", line)

                if match:
                    flood_packets += int(match.group(1))

        return flood_packets

    except Exception as e:
        print(f"[ERROR] Flood stats failed: {e}")
        return 0


# =========================================================
# 3. PORT TRAFFIC
# =========================================================

def get_port_traffic(sw):
    """
    Fetch port statistics
    """

    try:
        output = run_cmd(f"ovs-ofctl dump-ports {sw}")

        total_rx = 0
        total_tx = 0

        rx_matches = re.findall(r"rx pkts=\d+, bytes=(\d+)", output)
        tx_matches = re.findall(r"tx pkts=\d+, bytes=(\d+)", output)

        total_rx = sum(map(int, rx_matches))
        total_tx = sum(map(int, tx_matches))

        bandwidth = total_rx + total_tx

        return bandwidth

    except Exception as e:
        print(f"[ERROR] Port stats failed: {e}")
        return 0


# =========================================================
# 4. ENTRY AGE
# =========================================================

def calculate_entry_age(mac_entries):

    if not mac_entries:
        return 0

    ages = [entry["age"] for entry in mac_entries]

    return sum(ages) / len(ages)


# =========================================================
# 5. NEW MAC RATE
# =========================================================

def calculate_new_mac_rate(mac_entries):
    """
    Calculate rate of new MAC arrivals
    """

    global previous_mac_set

    current_mac_set = set()

    for entry in mac_entries:
        current_mac_set.add(entry["mac"])

    new_entries = current_mac_set - previous_mac_set

    rate = len(new_entries) / INTERVAL

    previous_mac_set = current_mac_set

    return rate


# =========================================================
# NORMALIZATION
# =========================================================

def normalize(value, max_value):

    if max_value == 0:
        return 0

    return round(value / max_value, 4)


# =========================================================
# MAIN MONITOR LOOP
# =========================================================

def monitor():

    print("\n========== SDN MONITOR STARTED ==========\n")

    while True:

        for sw in SWITCHES:

            print(f"\n========== SWITCH {sw} ==========")

            # -----------------------------------
            # MAC TABLE
            # -----------------------------------

            mac_entries = get_mac_table_entries(sw)

            current_entries = len(mac_entries)

            mac_fill = normalize(
                current_entries,
                MAX_MAC_CAPACITY
            )

            # -----------------------------------
            # FLOOD PRESSURE
            # -----------------------------------

            flood_rate = get_flood_pressure(sw)

            flood_pressure = normalize(
                flood_rate,
                MAX_FLOOD_RATE
            )

            # -----------------------------------
            # PORT TRAFFIC
            # -----------------------------------

            bandwidth = get_port_traffic(sw)

            traffic_load = normalize(
                bandwidth,
                MAX_BANDWIDTH
            )

            # -----------------------------------
            # ENTRY AGE
            # -----------------------------------

            avg_age = calculate_entry_age(mac_entries)

            age_score = normalize(
                avg_age,
                MAX_ENTRY_AGE
            )

            # -----------------------------------
            # NEW MAC RATE
            # -----------------------------------

            new_mac_rate = calculate_new_mac_rate(mac_entries)

            mac_growth = normalize(
                new_mac_rate,
                MAX_MAC_RATE
            )

            # ===================================
            # PRINT RESULTS
            # ===================================

            print(f"\n[1] MAC Table Entries")
            print(f"Current Entries : {current_entries}")
            print(f"Fill Percentage : {mac_fill}")

            print(f"\n[2] Flood Pressure")
            print(f"Flood Packets   : {flood_rate}")
            print(f"Flood Score     : {flood_pressure}")

            print(f"\n[3] Port Traffic")
            print(f"Bandwidth Usage : {bandwidth} bytes")
            print(f"Traffic Score   : {traffic_load}")

            print(f"\n[4] Entry Age")
            print(f"Average Age     : {avg_age:.2f} sec")
            print(f"Age Score       : {age_score}")

            print(f"\n[5] New MAC Rate")
            print(f"New MAC/sec     : {new_mac_rate:.2f}")
            print(f"Growth Score    : {mac_growth}")

            # ===================================
            # DECISION SIGNALS
            # ===================================

            if mac_fill > 0.85:
                print("\n[WARNING] MAC table nearing capacity!")

            if mac_fill > 0.95:
                print("[EMERGENCY] MAC table overflow risk!")

            if flood_pressure > 0.7:
                print("[ALERT] High flooding detected!")

            if age_score > 0.7:
                print("[ALERT] Stale MAC entries detected!")

            if mac_growth > 0.7:
                print("[ALERT] Possible MAC flood attack!")

        time.sleep(INTERVAL)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    monitor()