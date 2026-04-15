from mininet.net import Mininet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
import time
import subprocess #run command in linux and gets output
import csv

def print_fdb(switch):
    print("\n===== MAC TABLE for {} =====").format(switch)

    try:
        output = subprocess.check_output(
            ["ovs-appctl", "fdb/show", switch]
        )
        entries = parse_fdb(output)
        for e in entries:
            #print(e)
            data = {
                "event_type": "mac_entry",
                "switch": switch,
                "port": e["port"],
                "vlan": e["vlan"],
                "mac": e["mac"],
                "age": e["age"],
                "timestamp": int(time.time())
            }
            print(data)

            '''print("Port: {}, MAC: {}, Age: {}").format(
                e["port"], e["mac"], e["age"]
            )'''

    except Exception as e:
        print("Error:", e)

def parse_fdb(output):
    lines = output.splitlines()
    result = []

    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) == 4:
            result.append({
                "port": parts[0],
                "vlan": parts[1],
                "mac": parts[2],
                "age": parts[3]
            })

    return result

def get_port_info(port_name):
    port_info  = {}
    for port in port_name:

        #About interface 
        unicode_info = subprocess.check_output(["ovs-vsctl", "get", "interface", port, "admin_state", "link_state", "ofport", "duplex", "link_speed", "mtu"]).decode("utf-8").split()
        #print(unicode_info)
        info = [str(x) for x in unicode_info]
        if info[0] == 'up' and info[1] == 'up' and info[2] != '-1':
            status = "up"

        #About link
            unicode_link_info = subprocess.check_output(["ovs-vsctl", "--columns=tag,trunks,vlan_mode", "--format=csv", "--no-headings", "list", "port",  port]).decode("utf-8").strip()
            #print(unicode_link_info)
            link_info = next(csv.reader([unicode_link_info])) 
            #print(link_info)
            vlan = None
            if link_info[0] != '[]': # when link is access
                vlan = link_info[0]
            else:
                vlan = link_info[1] #when link is trunk
        
        
        info_data = {"status":status,
                    "vlan":vlan,
                    "vlan_mode":link_info[2],
                    "duplex":info[3],
                    "speed":info[4],
                    "mtu":info[5]                     
            }
        port_info[port] = info_data

    #print(port_info)
    return port_info
    

def get_portname():
    port_name = []
    try:
        for bridge in subprocess.check_output(["ovs-vsctl", "list-br"]).decode("utf-8").split(): #it gives byte object as output without decode()
            ports = subprocess.check_output(["ovs-vsctl", "list-ports", bridge]).decode("utf-8").split() #give ports name associated with particular bridge
            #print(bridge, ports)
            
            for port in ports: #converting unicode str into string
                port_name.append(str(port))
        
        #print(port_name)

        return port_name

    except Exception as e:
        print("Error:", e)
        return []

def vlan_info(port_info):
    vlan_map = {}

    for port, data in port_info.items():
        vlan_id = data['vlan']

        if vlan_id not in vlan_map: #multiple ports have same vlan
            vlan_map[vlan_id] = {} 
            vlan_map[vlan_id]["ports"] = [] # port list

        vlan_map[vlan_id]["ports"].append(port)
        vlan_map[vlan_id]["type"] = data['vlan_mode'] 

    #print(vlan_map)
    return vlan_map

def get_stats_info(port_name):
    stats_info = {}
    for port in port_name:
        output = subprocess.check_output(["ovs-vsctl", "get", "interface", port, "statistics"]).decode("utf-8").strip()
        #print(output) 
        all_stats = parse_stat_map(output) #give python dict

        #total error is sum of all errors
        total_error = (
            all_stats.get("rx_over_err", 0) +  # if value not present it raise an error, so give it 0
            all_stats.get("rx_frame_err", 0) +
            all_stats.get("tx_errors", 0) +
            all_stats.get("rx_crc_err", 0) +
            all_stats.get("rx_missed_errors", 0)
        )
              
        #total drops is sum of sending and receiving drops 
        total_drops = (
            all_stats.get("tx_dropped", 0) +  # if value not present it raise an error, so give it 0
            all_stats.get("rx_dropped", 0)
        )

        stats_info[port] = {
            "rx_packets": all_stats["rx_packets"], #incoming traffic
            "tx_packets": all_stats["tx_packets"], #outgoinf traffic
            "rx_bytes": all_stats["rx_bytes"],
            "tx_bytes": all_stats["tx_bytes"],
            "errors": total_error,
            "drops": total_drops
        }
    
    #print(stats_info)
    return stats_info


def parse_stat_map(output):
    output = output.strip("{} \n")
    #print(output)
    result = {}
    if not output:
        return result

    for item in output.split(","): # using of .split(), stats values with = between them split into list 
        #print(item)
        if "=" in item:
            k, v = item.split("=") # divide "collisions=0" -> [u"collisions", "0"]
            result[str(k.strip())] = int(v.strip()) #str() - convert unicode string

    return result

def topology():

    net = Mininet(controller=None)

    #c0 = net.addController('c0')

    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')
    h4 = net.addHost('h4')
    h5 = net.addHost('h5')
    h6 = net.addHost('h6')
    h7 = net.addHost('h7')
    h8 = net.addHost('h8')

    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)

    net.addLink(h5, s2)
    net.addLink(h6, s2)
    net.addLink(h7, s2)
    net.addLink(h8, s2)

    net.addLink(s1, s2)

    #STP Check
    #net.addLink(s1, s2)

    net.start()

    #Completely remove dependencies of controller over switches acts as normal learning switch    
    s1.cmd("ovs-vsctl set-fail-mode s1 standalone")
    s2.cmd("ovs-vsctl set-fail-mode s2 standalone")
    
    """
    print("Running pingall...\n")
    net.pingAll()

    # Print MAC tables BEFORE VLAN Configuration
    print_fdb("s1")
    print_fdb("s2")
    """

    """
    # comment it for STP Check
    s1.cmd("ovs-vsctl set Bridge s1 stp_enable=true")
    s2.cmd("ovs-vsctl set Bridge s2 stp_enable=true")
    """

    # VLAN tagging
    s1.cmd("ovs-vsctl set port s1-eth1 tag=10 vlan_mode=access")
    s1.cmd("ovs-vsctl set port s1-eth2 tag=10 vlan_mode=access")
    s1.cmd("ovs-vsctl set port s1-eth3 tag=20 vlan_mode=access")
    s1.cmd("ovs-vsctl set port s1-eth4 tag=20 vlan_mode=access")

    s2.cmd("ovs-vsctl set port s2-eth1 tag=10 vlan_mode=access")
    s2.cmd("ovs-vsctl set port s2-eth2 tag=10 vlan_mode=access")
    s2.cmd("ovs-vsctl set port s2-eth3 tag=20 vlan_mode=access")
    s2.cmd("ovs-vsctl set port s2-eth4 tag=20 vlan_mode=access")

    # trunk link between switches
    s1.cmd("ovs-vsctl set port s1-eth5 trunks=10,20 vlan_mode=trunk")
    s2.cmd("ovs-vsctl set port s2-eth5 trunks=10,20 vlan_mode=trunk")

    '''
    print("Running pingall after VLAN tagging...\n")
    # net.pingAll()
    net.pingAll(timeout=0.5) #it takes less time compared to normal pingAll

    # Print MAC tables After VALN Configuration
    print_fdb("s1")
    print_fdb("s2")
    '''

    #fetch port_names
    port_name = get_portname()
    
    #fetch port info
    port_info = get_port_info(port_name)

    #fetch ports in a particular vlan
    vlan_data = vlan_info(port_info)

    #get statictics info about ports
    stat_info = get_stats_info(port_name)

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()


