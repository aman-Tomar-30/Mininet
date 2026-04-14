from mininet.net import Mininet
from mininet.node import RemoteController, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel
import time
import subprocess

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
        unicode_info = subprocess.check_output(["ovs-vsctl", "get", "interface", port, "admin_state", "link_state", "ofport", "duplex", "link_speed", "mtu"]).decode().split()
        print(unicode_info)
        info = [str(x) for x in unicode_info]
        if info[0] == 'up' and info[1] == 'up' and info[2] != '-1':
            status = "up"
        
        
        info_data = { "status":status,
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
        for bridge in subprocess.check_output(["ovs-vsctl", "list-br"]).decode().split(): #it gives byte object as output without decode()
            ports = subprocess.check_output(["ovs-vsctl", "list-ports", bridge]).decode().split()
            #print(bridge, ports)
            for port in ports: #converting unicode str into string
                port_name.append(str(port))
        
        #print(port_name)

        return port_name

    except Exception as e:
        print("Error:", e)
        return []



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
    
    s1.cmd("ovs-vsctl set-fail-mode s1 standalone")
    s2.cmd("ovs-vsctl set-fail-mode s2 standalone")

    print("Running pingall...\n")
    net.pingAll()

    # Print MAC tables BEFORE CLI
    print_fdb("s1")
    print_fdb("s2")

    """
    STP Check
    s1.cmd("ovs-vsctl set Bridge s1 stp_enable=true")
    s2.cmd("ovs-vsctl set Bridge s2 stp_enable=true")
    """

    # VLAN tagging
    s1.cmd("ovs-vsctl set port s1-eth1 tag=10")
    s1.cmd("ovs-vsctl set port s1-eth2 tag=10")
    s1.cmd("ovs-vsctl set port s1-eth3 tag=20")
    s1.cmd("ovs-vsctl set port s1-eth4 tag=20")

    s2.cmd("ovs-vsctl set port s2-eth1 tag=10")
    s2.cmd("ovs-vsctl set port s2-eth2 tag=10")
    s2.cmd("ovs-vsctl set port s2-eth3 tag=20")
    s2.cmd("ovs-vsctl set port s2-eth4 tag=20")

    # trunk link between switches
    s1.cmd("ovs-vsctl set port s1-eth5 trunks=10,20")
    s2.cmd("ovs-vsctl set port s2-eth5 trunks=10,20")

    '''
    print("Running pingall after VLAN tagging...\n")
    # net.pingAll()
    net.pingAll(timeout=0.5) #it takes less time compared to normal pingAll

    # Print MAC tables After VALN Tagging
    print_fdb("s1")
    print_fdb("s2")
    '''

    #fetch port_names
    port_name = get_portname()
    get_port_info(port_name)


    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()


