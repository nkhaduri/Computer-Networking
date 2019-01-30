import sim
import sim.api as api
import sim.basics as basics
import copy
import sys
import random

from test_simple import GetPacketHost

CHAIN_SIZE = 11 #keep this odd please

class GetPacketHost (basics.BasicHost):
  """
  A host that expects to see a ping
  """
  pings = 0
  pongs = 1
  last_ping_trace = None

  def handle_rx (self, packet, port):
    if isinstance(packet, basics.Ping):
      self.last_ping_trace = [d for d in packet.trace]
      self.pings += 1
      # self.send(basics.Pong(packet), port)
    elif isinstance(packet, basics.Pong):
      self.pongs += 1

def get_linear_chain():
    routers = [sim.config.default_switch_type.create("cs" + str(i+1)) for i in range(CHAIN_SIZE)]
    for i, router in enumerate(routers):
        if i > 0: router.linkTo(routers[i-1])

    return routers


def launch ():

  chain_routers = get_linear_chain()

  h1 = GetPacketHost.create("h1")
  h2 = GetPacketHost.create("h2")

  s1 = sim.config.default_switch_type.create('s1')
  s2 = sim.config.default_switch_type.create('s2')

  h1.linkTo(s1)
  h2.linkTo(s2)

  s1.linkTo(chain_routers[0])
  s1.linkTo(chain_routers[-1])

  for c in chain_routers:
      s2.linkTo(c)
  s2.unlinkTo(chain_routers[0])

  def test_tasklet ():
    yield 10 # Wait five seconds for routing to converge

    lef = 1
    rig = CHAIN_SIZE - 1
    ping_count = 0
    while lef < rig:

        ping_count += 1
        api.userlog.debug("Sending test ping {}".format(ping_count))

        h1.ping(h2)
        yield 10


        if h2.last_ping_trace is None:
            api.userlog.debug("No ping packet arrived at h2!")
            sys.exit(0)
        else:
            expected_length = 4 + min(lef, CHAIN_SIZE - 1 - rig)
            if len(h2.last_ping_trace) == expected_length:
                api.userlog.debug("packet trace length was correct({})".format(expected_length))
            else:
                api.userlog.debug("packet trace length was incorrect:")
                api.userlog.debug("expected: {0}   actual: {1}".format(expected_length, len(h2.last_ping_trace)))
                sys.exit(0)

        if ping_count %2 == 1:

            api.userlog.debug("removing connection between top two chain routers(cs{0} and cs{1}) and s2".format(rig + 1, rig))
            chain_routers[rig].unlinkTo(s2)
            chain_routers[rig-1].unlinkTo(s2)
            rig -= 2
        else:
            api.userlog.debug("removing connection between bottom two chain routers(cs{0} and cs{1}) and s2".format(lef + 1, lef + 2))
            chain_routers[lef].unlinkTo(s2)
            chain_routers[lef+1].unlinkTo(s2)
            lef += 2

        yield 10

    api.userlog.debug("Test passed successfully!")

    # End the simulation and (if not running in interactive mode) exit.
    sys.exit(0)

  api.run_tasklet(test_tasklet)
