"""
Your awesome Distance Vector router for CS 168
"""

import sim.api as api
import sim.basics as basics


# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter (basics.DVRouterBase):
  # NO_LOG = True # Set to True on an instance to disable its logging
  POISON_MODE = True # Can override POISON_MODE here
  # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing


  def __init__ (self):
    """
    Called when the instance is initialized.

    You probably want to do some additional initialization here.
    """
    self.start_timer() # Starts calling handle_timer() at correct rate
    self.f_table = {}
    self.latencies = {}
    self.direct_hosts = {}

  def broadcast_route(self, port, destination, latency):
    packet = basics.RoutePacket(destination, latency)
    self.send(packet, port, flood=True)

  def update_all_neighbors(self):
    for dst in self.f_table:
      if api.current_time() - self.f_table[dst]['time'] <= 15:
        self.broadcast_route(self.f_table[dst]['port'], dst, self.f_table[dst]['dist'])
      elif dst in self.direct_hosts:
        self.f_table[dst] = {'port': self.direct_hosts[dst], 'dist': self.latencies[self.direct_hosts[dst]], 'time': float('inf')}
        self.broadcast_route(self.direct_hosts[dst], dst, self.latencies[self.direct_hosts[dst]])


  def handle_link_up (self, port, latency):
    """
    Called by the framework when a link attached to this Entity goes up.

    The port attached to the link and the link latency are passed in.
    """
    if port in self.latencies:
      for dst in self.f_table:
        if self.f_table[dst]['port'] == port:
          self.f_table[dst]['dist'] += latency - self.latencies[port]
          if dst in self.direct_hosts and self.latencies[self.direct_hosts[dst]] <= self.f_table[dst]['dist']:
            self.f_table = {'port': self.direct_hosts[dst], 'dist': self.latencies[self.direct_hosts[dst]], 'time': float('inf')}
            self.broadcast_route(self.direct_hosts[dst], dst, self.latencies[self.direct_hosts[dst]])
          elif self.f_table[dst]['dist'] >= INFINITY:
            self.f_table[dst] = {'port': -1, 'dist': float('inf'), 'time': -1}
            if self.POISON_MODE:
              self.broadcast_route(None, dst, float('inf'))
    else:
      for dst in self.f_table:
        if api.current_time() - self.f_table[dst]['time'] <= 15:
          self.send(basics.RoutePacket(dst, self.f_table[dst]['dist']), port)
    self.latencies[port] = latency

  def handle_link_down (self, port):
    """
    Called by the framework when a link attached to this Entity does down.

    The port number used by the link is passed in.
    """
    for dst in self.f_table:
      if self.f_table[dst]['port'] == port:
        if dst not in self.direct_hosts or self.direct_hosts[dst] == port:
          self.f_table[dst] = {'port': -1, 'dist': float('inf'), 'time': -1}
          if self.POISON_MODE:
            self.broadcast_route(None, dst, float('inf'))
        else:
          self.f_table[dst] = {'port': self.direct_hosts[dst], 'dist': self.latencies[self.direct_hosts[dst]], 'time': float('inf')}
          self.broadcast_route(self.direct_hosts[dst], dst, self.latencies[self.direct_hosts[dst]])
    for host in dict(self.direct_hosts):
      if self.direct_hosts[host] == port:
        del self.direct_hosts[host]
    del self.latencies[port]

  def handle_rx (self, packet, port):
    """
    Called by the framework when this Entity receives a packet.

    packet is a Packet (or subclass).
    port is the port number it arrived on.

    You definitely want to fill this in.
    """
    #self.log("RX %s on %s (%s)", packet, port, api.current_time())
    if isinstance(packet, basics.RoutePacket):
      if packet.destination not in self.f_table or self.f_table[packet.destination]['port'] == port or\
          self.f_table[packet.destination]['dist'] > self.latencies[port] + packet.latency or\
          (self.f_table[packet.destination]['dist'] == self.latencies[port] + packet.latency and self.f_table[packet.destination]['time'] < api.current_time()):
        dist = self.latencies[port] + packet.latency if self.latencies[port] + packet.latency <= INFINITY else float('inf')
        
        if packet.destination in self.direct_hosts and self.latencies[self.direct_hosts[packet.destination]] <= dist:
          dist = self.latencies[self.direct_hosts[packet.destination]]
          self.f_table[packet.destination] = {'port': self.direct_hosts[packet.destination], 'dist': dist, 'time': float('inf')}
          self.broadcast_route(self.direct_hosts[packet.destination], packet.destination, dist)
        else:
          self.f_table[packet.destination] = {'port': port, 'dist': dist, 'time': api.current_time()}
          self.broadcast_route(port, packet.destination, dist)
    elif isinstance(packet, basics.HostDiscoveryPacket):
      self.direct_hosts[packet.src] = port
      if packet.src not in self.f_table or self.f_table[packet.src]['dist'] >= self.latencies[port]:
        self.f_table[packet.src] = {'port': port, 'dist': self.latencies[port], 'time': float('inf')}
        self.broadcast_route(port, packet.src, self.latencies[port])
    else:
      if packet.dst in self.f_table and self.f_table[packet.dst]['port'] != -1 and self.f_table[packet.dst]['dist'] != float('inf') and\
         api.current_time() - self.f_table[packet.dst]['time'] <= 15 and self.f_table[packet.dst]['port'] != port:
        self.send(packet, port=self.f_table[packet.dst]['port'])
      elif packet.dst in self.direct_hosts and (packet.dst not in self.f_table or self.f_table[packet.dst]['port'] != port):
        self.f_table[packet.dst] = {'port': self.direct_hosts[packet.dst], 'dist': self.latencies[self.direct_hosts[packet.dst]], 'time': float('inf')}
        self.broadcast_route(self.direct_hosts[packet.dst], packet.dst, self.latencies[self.direct_hosts[packet.dst]])
        self.send(packet, port=self.direct_hosts[packet.dst])

  def handle_timer (self):
    """
    Called periodically.

    When called, your router should send tables to neighbors.  It also might
    not be a bad place to check for whether any entries have expired.
    """
    self.update_all_neighbors()