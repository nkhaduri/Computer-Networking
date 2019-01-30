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

  hosts = [GetPacketHost.create("h{}".format(i)) for i in range(5)]


  s1 = sim.config.default_switch_type.create('s1')
  for h in hosts:
      h.linkTo(s1)


  def test_tasklet ():
    yield 10 # Wait five seconds for routing to converge


    api.userlog.debug("Sending ping from every host to every other host (totally {} hosts and one router)".format(len(hosts)))
    for h1 in hosts:
        for h2 in hosts:
            if h1 == h2: continue
            h1.ping(h2)


    yield 20


    wrong_hosts = [h for h in hosts if h.pings != len(hosts) - 1]
    if len(wrong_hosts) > 0:
      api.userlog.error("SOME HOSTS RECEIVED WRONG NUMBER OF PINGS:")
      for h in wrong_hosts:
          api.userlog.error("{0} got {1} pings instead of {2}".format(h.name, h.pings, len(hosts) - 1))
    else:
      api.userlog.debug("Test passed successfully!")

    # End the simulation and (if not running in interactive mode) exit.
    import sys
    sys.exit(0)

  api.run_tasklet(test_tasklet)
