import time
import xml.etree.ElementTree as ET
from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib import hub
from ryu.lib import igmplib, mac
from ryu.lib.dpid import str_to_dpid
from ryu.lib.packet import packet, arp, ethernet, ipv4, igmp
from ryu.topology import event
from ryu.topology.api import get_switch, get_link, get_host
import networkx as nx
import matplotlib.pyplot as plt
import setting
from setting import print_pretty_table, print_pretty_list
class NetworkStructure(app_manager.RyuApp):
    
    OFP_VERSION = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(NetworkStructure, self).__init__(*args, **kwargs)
        self.start_time = time.time()
        self.name = 'discovery'
        self.topology_api_app = self
        self.link_info_xml = setting.LINKS_INFO  
        self.m_graph = self.parse_topo_links_info()  
        self.graph = nx.Graph()
        self.pre_graph = nx.Graph()
        self.access_table = {}  
        self.switch_all_ports_table = {}  
        self.all_switches_dpid = {}  
        self.switch_port_table = {}  
        self.link_port_table = {}  
        self.not_use_ports = {}  
        self.shortest_path_table = {}  
        self.arp_table = {}  
        self.arp_src_dst_ip_table = {}
        self.initiation_delay = setting.INIT_TIME
        self.first_flag = True
        self.cal_path_flag = False
        self._structure_thread = hub.spawn(self.scheduler)
        self._shortest_path_thread = hub.spawn(self.cal_shortest_path_thread)
    def print_parameters(self):
        logger = self.logger.info if setting.LOGGER else print
        print_pretty_table(self.switch_all_ports_table, ['dpid', 'port_no'], [10, 10],
                           'SSSS switch_all_ports_table', logger)
        print_pretty_table(self.switch_port_table, ['dpid', 'port_no'], [10, 10], 'SSSS switch_port_table',
                           logger)
        print_pretty_table(self.access_table, ['(dpid, in_port)', '(src_ip, src_mac)'], [10, 40], 'SSSS access_table',
                           logger)
        print_pretty_table(self.not_use_ports, ['dpid', 'not_use_ports'], [10, 30], 'SSSS not_use_ports', logger)
    def scheduler(self):
        i = 0
        while True:
            if i == 3:
                self.get_topology(None)
                i = 0
            hub.sleep(setting.DISCOVERY_PERIOD)
            if setting.PRINT_SHOW:
                self.print_parameters()
            i += 1
    def cal_shortest_path_thread(self):
        self.cal_path_flag = False
        while True:
            if self.cal_path_flag:
                self.calculate_all_nodes_shortest_paths(weight=setting.WEIGHT)
            hub.sleep(setting.DISCOVERY_PERIOD)
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.logger.info("discovery---> switch: %s connected", datapath.id)
        match = parser.OFPMatch()  
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
    def add_flow(self, datapath, priority, match, actions):
        inst = [datapath.ofproto_parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS,
                                                              actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(datapath=datapath, priority=priority,
                                                 match=match, instructions=inst)
        datapath.send_msg(mod)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)
        if isinstance(arp_pkt, arp.arp):
            arp_src_ip = arp_pkt.src_ip
            src_mac = arp_pkt.src_mac
            self.storage_access_info(datapath.id, in_port, arp_src_ip, src_mac)
    def storage_access_info(self, dpid, in_port, src_ip, src_mac):
        if in_port in self.not_use_ports[dpid]:
            if (dpid, in_port) in self.access_table:
                if self.access_table[(dpid, in_port)] == (src_ip, src_mac):
                    return
                else:
                    self.access_table[(dpid, in_port)] = (src_ip, src_mac)
                    return
            else:
                self.access_table.setdefault((dpid, in_port), None)
                self.access_table[(dpid, in_port)] = (src_ip, src_mac)
                return
    events = [event.EventSwitchEnter, event.EventSwitchLeave,
              event.EventPortAdd, event.EventPortDelete, event.EventPortModify,
              event.EventLinkAdd, event.EventLinkDelete]
    @set_ev_cls(events)
    def get_topology(self, ev):
        present_time = time.time()
        if present_time - self.start_time < self.initiation_delay:  
            print(f'SSSS--->get_topology: need to WAIT {self.initiation_delay - (present_time - self.start_time):.2f}s')
            return
        elif self.first_flag:
            self.first_flag = False
            print("SSSS--->get_topology: complete WAIT")
        self.logger.info("[Topology Discovery Ok]")
        switch_list = get_switch(self.topology_api_app, None)
        for switch in switch_list:
            dpid = switch.dp.id
            self.switch_all_ports_table.setdefault(dpid, set())
            self.switch_port_table.setdefault(dpid, set())
            self.not_use_ports.setdefault(dpid, set())
            for p in switch.ports:
                self.switch_all_ports_table[dpid].add(p.port_no)
        self.all_switches_dpid = self.switch_all_ports_table.keys()
        link_list = get_link(self.topology_api_app, None)
        for link in link_list:
            src = link.src  
            dst = link.dst
            self.link_port_table[(src.dpid, dst.dpid)] = (src.port_no, dst.port_no)
            if src.dpid in self.all_switches_dpid:
                self.switch_port_table[src.dpid].add(src.port_no)
            if dst.dpid in self.all_switches_dpid:
                self.switch_port_table[dst.dpid].add(dst.port_no)
        for sw_dpid in self.switch_all_ports_table.keys():
            all_ports = self.switch_all_ports_table[sw_dpid]
            linked_port = self.switch_port_table[sw_dpid]
            self.not_use_ports[sw_dpid] = all_ports - linked_port
        self.build_topology_between_switches()
        self.cal_path_flag = True
    def build_topology_between_switches(self, bw=0, delay=0, loss=0):
        
        _graph = nx.Graph()
        for (src_dpid, dst_dpid) in self.link_port_table.keys():
            _graph.add_edge(src_dpid, dst_dpid, bw=bw, delay=delay, loss=loss)
        if _graph.edges == self.graph.edges:
            return 
        else:
            self.graph = _graph
    def calculate_weight(self, node1, node2, weight_dict):
        
        assert 'bw' in weight_dict and 'delay' in weight_dict, "edge weight should have bw and delay"
        try:
            weight = weight_dict['bw'] * setting.FACTOR - weight_dict['delay'] * (1 - setting.FACTOR)
            return weight
        except TypeError:
            print("discovery ERROR---> weight_dict['bw']: ", weight_dict['bw'])
            print("discovery ERROR---> weight_dict['delay']: ", weight_dict['delay'])
            return None
    def get_shortest_paths(self, src_dpid, dst_dpid, weight=None):
        
        graph = self.graph.copy()
        self.shortest_path_table[(src_dpid, dst_dpid)] = nx.shortest_path(graph,
                                                                          source=src_dpid,
                                                                          target=dst_dpid,
                                                                          weight=weight,
                                                                          method=setting.METHOD)
    def calculate_all_nodes_shortest_paths(self, weight=None):
        
        self.shortest_path_table = {}  
        for src in self.graph.nodes():
            for dst in self.graph.nodes():
                if src != dst:
                    self.get_shortest_paths(src, dst, weight=weight)
                else:
                    continue
    def get_host_ip_location(self, host_ip):
        
        if host_ip == "0.0.0.0" or host_ip == "255.255.255.255":
            return None
        for key in self.access_table.keys():  
            if self.access_table[key][0] == host_ip:
                return key
        print("SSS--->get_host_ip_location: %s location is not found" % host_ip)
        return None
    def get_ip_by_dpid(self, dpid):
        
        for key, value in self.access_table.items():
            if key[0] == dpid:
                return value[0]
        print("SSS--->get_ip_by_dpid: %s ip is not found" % dpid)
        return None
    def parse_topo_links_info(self):
        m_graph = nx.Graph()
        parser = ET.parse(self.link_info_xml)
        root = parser.getroot()
        def _str_tuple2int_list(s: str):
            s = s.strip()
            assert s.startswith('(') and s.endswith(")"), '应该为str的元组，如 "(1, 2)"'
            s_ = s[1: -1].split(', ')
            return [int(i) for i in s_]
        node1, node2, port1, port2, bw, delay, loss = None, None, None, None, None, None, None
        for e in root.iter():
            if e.tag == 'links':
                node1, node2 = _str_tuple2int_list(e.text)
            elif e.tag == 'ports':
                port1, port2 = _str_tuple2int_list(e.text)
            elif e.tag == 'bw':
                bw = float(e.text)
            elif e.tag == 'delay':
                delay = float(e.text[:-2])
            elif e.tag == 'loss':
                loss = float(e.text)
            else:
                print(e.tag)
                continue
            m_graph.add_edge(node1, node2, port1=port1, port2=port2, bw=bw, delay=delay, loss=loss)
        for edge in m_graph.edges(data=True):
            print(edge)
        return m_graph
