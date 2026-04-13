from mininet.net import Mininet
from mininet.node import RemoteController, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel

import subprocess

def print_fdb(switch):
    print("\n===== MAC TABLE for {} =====").format(switch)

    try:
        output = subprocess.check_output(
            ["ovs-appctl", "fdb/show", switch]
        )
        entries = parse_fdb(output)
        for e in entries:
            print("Port: {}, MAC: {}, Age: {}").format(
                e["port"], e["mac"], e["age"]
            )
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
#    s1.cmd("ovs-vsctl set port s1-eth1 tag=10")
#    s1.cmd("ovs-vsctl set port s1-eth2 tag=20")
#    s1.cmd("ovs-vsctl set port s1-eth3 tag=30")
#    s1.cmd("ovs-vsctl set port s1-eth4 tag=40")

#    s2.cmd("ovs-vsctl set port s2-eth1 tag=10")
#    s2.cmd("ovs-vsctl set port s2-eth2 tag=20")
#    s2.cmd("ovs-vsctl set port s2-eth3 tag=30")
#    s2.cmd("ovs-vsctl set port s2-eth4 tag=40")

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()


