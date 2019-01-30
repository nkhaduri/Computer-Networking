import sim
import sim.api as api
import sim.basics as basics


from test_simple import GetPacketHost


class GetPacketHost (basics.BasicHost):
  """
  A host that expects to see a ping
  """
  pings = 0
  def handle_rx (self, packet, port):
    if isinstance(packet, basics.Ping):
      self.pings += 1


def launch ():
  h1 = GetPacketHost.create("h1")
  h2 = GetPacketHost.create("h2")

  s1 = sim.config.default_switch_type.create('s1')
  s2 = sim.config.default_switch_type.create('s2')

  h1.linkTo(s1)
  h2.linkTo(s2)

  s1.linkTo(s2)

  def test_tasklet ():
    yield 10 # Wait five seconds for routing to converge

    api.userlog.debug("Sending test ping 1 (should get there)")
    h1.ping(h2)

    yield 10

    api.userlog.debug("Failing s1-s2 link")
    s1.unlinkTo(s2)

    yield 10

    api.userlog.debug("Sending test ping 2 (should not get there)")
    h1.ping(h2)

    yield 10

    api.userlog.debug("Reconnecting s1 and s2")
    s1.linkTo(s2)

    yield 10

    api.userlog.debug("Sending test ping 2 (should get there)")
    h1.ping(h2)

    yield 10

    if h2.pings != 2:
      api.userlog.error("h2 got %s packets instead of 2", h2.pings)
    else:
      api.userlog.debug("Test passed successfully!")

    # End the simulation and (if not running in interactive mode) exit.
    import sys
    sys.exit(0)

  api.run_tasklet(test_tasklet)
