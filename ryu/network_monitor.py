from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib import hub
from ryu.base.app_manager import lookup_service_brick
import setting
from setting import print_pretty_table, print_pretty_list
class NetworkMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(NetworkMonitor, self).__init__(*args, **kwargs)
        self.name = 'monitor'
        self.datapaths_table = {}
        self.dpid_port_fueatures_table = {}
        self.port_stats_table = {}
        self.flow_stats_table = {}
        self.port_speed_table = {}
        self.flow_speed_table = {}
        self.port_flow_dpid_stats = {'port': {}, 'flow': {}}
        self.port_curr_speed = {}
        self.port_loss = {}
        self.discovery = lookup_service_brick("discovery")  
        self.monitor_thread = hub.spawn(self.scheduler)
        self.save_thread = hub.spawn(self.save_bw_loss_graph)
    def scheduler(self):
        while True:
            self.port_flow_dpid_stats['flow'] = {}
            self.port_flow_dpid_stats['port'] = {}
            self._request_stats()
            hub.sleep(setting.MONITOR_PERIOD)
    def save_bw_loss_graph(self):
        while True:
            self.create_bandwidth_graph()
            self.create_loss_graph()
            hub.sleep(setting.MONITOR_PERIOD)
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath  
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths_table:
                self.datapaths_table[datapath.id] = datapath
                self.dpid_port_fueatures_table.setdefault(datapath.id, {})
                self.flow_stats_table.setdefault(datapath.id, {})
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths_table:
                del self.datapaths_table[datapath.id]
    def _request_stats(self):
        datapaths_table = self.datapaths_table.values()
        for datapath in list(datapaths_table):
            self.dpid_port_fueatures_table.setdefault(datapath.id, {})
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            req = parser.OFPPortDescStatsRequest(datapath, 0)  
            datapath.send_msg(req)
            req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)  
            datapath.send_msg(req)
    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto
        config_dict = {ofproto.OFPPC_PORT_DOWN: 'Port Down',
                       ofproto.OFPPC_NO_RECV: 'No Recv',
                       ofproto.OFPPC_NO_FWD: 'No Forward',
                       ofproto.OFPPC_NO_PACKET_IN: 'No Pakcet-In'}
        state_dict = {ofproto.OFPPS_LINK_DOWN: "Link Down",
                      ofproto.OFPPS_BLOCKED: "Blocked",
                      ofproto.OFPPS_LIVE: "Live"}
        for ofport in ev.msg.body:  
            if ofport.port_no != ofproto_v1_3.OFPP_LOCAL: 
                if ofport.config in config_dict:
                    config = config_dict[ofport.config]
                else:  
                    config = 'Up'
                if ofport.state in state_dict:
                    state = state_dict[ofport.state]
                else:
                    state = 'Up'
                port_features = (config, state, ofport.curr_speed, ofport.max_speed)
                self.dpid_port_fueatures_table[dpid][ofport.port_no] = port_features
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_table_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        self.port_flow_dpid_stats['port'][dpid] = body
        for stat in sorted(body, key=attrgetter("port_no")):
            port_no = stat.port_no
            if port_no != ofproto_v1_3.OFPP_LOCAL:
                key = (dpid, port_no)
                value = (stat.tx_bytes, stat.rx_bytes, stat.rx_errors,
                         stat.duration_sec, stat.duration_nsec, stat.tx_packets, stat.rx_packets)
                self._save_stats(self.port_stats_table, key, value, 5)  
                pre_bytes = 0
                delta_time = setting.SCHEDULE_PERIOD
                stats = self.port_stats_table[key]  
                if len(stats) > 1:  
                    pre_bytes = stats[-2][0] + stats[-2][1]
                    delta_time = self._calculate_delta_time(stats[-1][3], stats[-1][4],
                                                            stats[-2][3], stats[-2][4])  
                speed = self._calculate_speed(stats[-1][0] + stats[-1][1],
                                              pre_bytes, delta_time)
                self._save_stats(self.port_speed_table, key, speed, 5)
                self._calculate_port_speed(dpid, port_no, speed)
        self.calculate_loss_of_link()
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        msg = ev.msg
        body = msg.body
        datapath = msg.datapath
        dpid = datapath.id
        self.port_flow_dpid_stats['flow'][dpid] = body
        for stat in sorted([flowstats for flowstats in body if flowstats.priority == 1],
                           key=lambda flowstats: (flowstats.match.get('in_port'), flowstats.match.get('ipv4_dst'))):
            key = (stat.match['in_port'], stat.match['ipv4_dst'],
                   stat.instructions[0].actions[0].port)
            value = (stat.packet_count, stat.byte_count, stat.duration_sec, stat.duration_nsec)
            self._save_stats(self.flow_stats_table[dpid], key, value, 5)
            pre_bytes = 0
            delta_time = setting.SCHEDULE_PERIOD
            value = self.flow_stats_table[dpid][key]
            if len(value) > 1:
                pre_bytes = value[-2][1]
                delta_time = self._calculate_delta_time(value[-1][2], value[-1][3],
                                                        value[-2][2], value[-2][3])
            speed = self._calculate_speed(self.flow_stats_table[dpid][key][-1][1], pre_bytes, delta_time)
            self.flow_speed_table.setdefault(dpid, {})
            self._save_stats(self.flow_speed_table[dpid], key, speed, 5)
    @staticmethod
    def _save_stats(_dict, key, value, keep):
        if key not in _dict:
            _dict[key] = []
        _dict[key].append(value)
        if len(_dict[key]) > keep:
            _dict[key].pop(0)  
    def _calculate_delta_time(self, now_sec, now_nsec, pre_sec, pre_nsec):
        return self._calculate_seconds(now_sec, now_nsec) - self._calculate_seconds(pre_sec, pre_nsec)
    @staticmethod
    def _calculate_seconds(sec, nsec):
        return sec + nsec / 10 ** 9
    @staticmethod
    def _calculate_speed(now_bytes, pre_bytes, delta_time):
        if delta_time:
            return (now_bytes - pre_bytes) / delta_time
        else:
            return 0
    def _calculate_port_speed(self, dpid, port_no, speed):
        curr_bw = speed * 8 / 10 ** 6  
        self.port_curr_speed.setdefault(dpid, {})
        self.port_curr_speed[dpid][port_no] = curr_bw
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        if msg.reason == ofp.OFPPR_ADD:
            reason = 'ADD'
        elif msg.reason == ofp.OFPPR_DELETE:
            reason = 'DELETE'
        elif msg.reason == ofp.OFPPR_MODIFY:
            reason = 'MODIFY'
        else:
            reason = 'unknown'
    def create_bandwidth_graph(self):
        for link in self.discovery.link_port_table:
            src_dpid, dst_dpid = link
            src_port, dst_port = self.discovery.link_port_table[link]
            if src_dpid in self.port_curr_speed.keys() and dst_dpid in self.port_curr_speed.keys():
                src_port_bw = self.port_curr_speed[src_dpid][src_port]
                dst_port_bw = self.port_curr_speed[dst_dpid][dst_port]
                src_dst_bandwidth = min(src_port_bw, dst_port_bw)  
                capacity = self.discovery.m_graph[src_dpid][dst_dpid]['bw']
                self.discovery.graph[src_dpid][dst_dpid]['bw'] = max(capacity - src_dst_bandwidth, 0)
            else:
                self.discovery.graph[src_dpid][dst_dpid]['bw'] = -1
    def calculate_loss_of_link(self):
        for link, port in self.discovery.link_port_table.items():
            src_dpid, dst_dpid = link
            src_port, dst_port = port
            if (src_dpid, src_port) in self.port_stats_table.keys() and \
                    (dst_dpid, dst_port) in self.port_stats_table.keys():
                tx = self.port_stats_table[(src_dpid, src_port)][-1][0]  
                rx = self.port_stats_table[(dst_dpid, dst_port)][-1][1]  
                loss_ratio = abs(float(tx - rx) / tx) * 100
                self._save_stats(self.port_loss, link, loss_ratio, 5)
                tx = self.port_stats_table[(dst_dpid, dst_port)][-1][0]  
                rx = self.port_stats_table[(src_dpid, src_port)][-1][1]  
                loss_ratio = abs(float(tx - rx) / tx) * 100
                self._save_stats(self.port_loss, link[::-1], loss_ratio, 5)
            else:
                self.logger.info("MMMM--->  calculate_loss_of_link error", )
    def update_graph_loss(self):
        for link in self.discovery.link_port_table:
            src_dpid = link[0]
            dst_dpid = link[1]
            if link in self.port_loss.keys() and link[::-1] in self.port_loss.keys():
                src_loss = self.port_loss[link][-1]
                dst_loss = self.port_loss[link[::-1]][-1]
                link_loss = max(src_loss, dst_loss)  
                self.discovery.graph[src_dpid][dst_dpid]['loss'] = link_loss
            else:
                self.discovery.graph[src_dpid][dst_dpid]['loss'] = 100
    def create_loss_graph(self):
        self.update_graph_loss()
