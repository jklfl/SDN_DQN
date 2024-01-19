#!/usr/bin/python
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch
from mininet.topo import Topo
class fatTreeTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        h7 = self.addHost('h7', cls=Host, ip='10.0.0.7', defaultRoute=None)
        h8 = self.addHost('h8', cls=Host, ip='10.0.0.8', defaultRoute=None)
        h1 = self.addHost('h1', cls=Host, ip='10.0.0.1', defaultRoute=None)
        h2 = self.addHost('h2', cls=Host, ip='10.0.0.2', defaultRoute=None)
        h4 = self.addHost('h4', cls=Host, ip='10.0.0.4', defaultRoute=None)
        h3 = self.addHost('h3', cls=Host, ip='10.0.0.3', defaultRoute=None)
        h5 = self.addHost('h5', cls=Host, ip='10.0.0.5', defaultRoute=None)
        h6 = self.addHost('h6', cls=Host, ip='10.0.0.6', defaultRoute=None)
        h9 = self.addHost('h9', cls=Host, ip='10.0.0.9', defaultRoute=None)
        h10 = self.addHost('h8', cls=Host, ip='10.0.0.10', defaultRoute=None)
        h11 = self.addHost('h1', cls=Host, ip='10.0.0.11', defaultRoute=None)
        h12 = self.addHost('h2', cls=Host, ip='10.0.0.12', defaultRoute=None)
        h14 = self.addHost('h4', cls=Host, ip='10.0.0.14', defaultRoute=None)
        h13 = self.addHost('h3', cls=Host, ip='10.0.0.13', defaultRoute=None)
        h15 = self.addHost('h5', cls=Host, ip='10.0.0.15', defaultRoute=None)
        h16 = self.addHost('h6', cls=Host, ip='10.0.0.16', defaultRoute=None)

        s1 = self.addSwitch('s1', cls=OVSKernelSwitch)
        s11 = self.addSwitch('s11', cls=OVSKernelSwitch)
        s12 = self.addSwitch('s12', cls=OVSKernelSwitch)
        s13 = self.addSwitch('s13', cls=OVSKernelSwitch)
        s14 = self.addSwitch('s14', cls=OVSKernelSwitch)

        s2 = self.addSwitch('s2', cls=OVSKernelSwitch)
        s23 = self.addSwitch('s23', cls=OVSKernelSwitch)
        s24 = self.addSwitch('s24', cls=OVSKernelSwitch)
        s21 = self.addSwitch('s21', cls=OVSKernelSwitch)
        s22 = self.addSwitch('s22', cls=OVSKernelSwitch)

        s3 = self.addSwitch('s3', cls=OVSKernelSwitch)
        s31 = self.addSwitch('s31', cls=OVSKernelSwitch)
        s32 = self.addSwitch('s32', cls=OVSKernelSwitch)
        s33 = self.addSwitch('s33', cls=OVSKernelSwitch)
        s34 = self.addSwitch('s34', cls=OVSKernelSwitch)

        s4 = self.addSwitch('s4', cls=OVSKernelSwitch)
        s41 = self.addSwitch('s41', cls=OVSKernelSwitch)
        s42 = self.addSwitch('s42', cls=OVSKernelSwitch)
        s43 = self.addSwitch('s43', cls=OVSKernelSwitch)
        s44 = self.addSwitch('s44', cls=OVSKernelSwitch)

        self.addLink(h1, s13)
        self.addLink(h2, s13)
        self.addLink(h3, s14)
        self.addLink(h4, s14)
        self.addLink(h5, s23)
        self.addLink(h6, s23)
        self.addLink(h7, s24)
        self.addLink(h8, s24)
        self.addLink(h9, s33)
        self.addLink(h10, s33)
        self.addLink(h11, s34)
        self.addLink(h12, s34)
        self.addLink(h13, s41)
        self.addLink(h14, s42)
        self.addLink(h15, s43)
        self.addLink(h16, s44)

        self.addLink(s11, s1)
        self.addLink(s11, s2)
        self.addLink(s11, s13)
        self.addLink(s11, s14)

        self.addLink(s12, s3)
        self.addLink(s12, s4)
        self.addLink(s12, s13)
        self.addLink(s12, s14)

        self.addLink(s21, s1)
        self.addLink(s21, s2)
        self.addLink(s21, s23)
        self.addLink(s21, s24)

        self.addLink(s22, s3)
        self.addLink(s22, s4)
        self.addLink(s22, s23)
        self.addLink(s22, s24)

        self.addLink(s31, s1)
        self.addLink(s31, s2)
        self.addLink(s31, s33)
        self.addLink(s31, s34)

        self.addLink(s32, s3)
        self.addLink(s32, s4)
        self.addLink(s32, s33)
        self.addLink(s32, s34)

        self.addLink(s41, s1)
        self.addLink(s41, s2)
        self.addLink(s41, s43)
        self.addLink(s41, s44)

        self.addLink(s42, s3)
        self.addLink(s42, s4)
        self.addLink(s42, s43)
        self.addLink(s42, s44)
        
topos = { 'mytopo': (lambda: fatTreeTopo() ) }