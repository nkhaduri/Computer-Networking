import sim
import sim.api as api
import sim.basics as basics
import copy
import sys

from test_simple import GetPacketHost


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
      self.send(basics.Pong(packet), port)
    elif isinstance(packet, basics.Pong):
      self.pongs += 1


def launch ():

  h1 = GetPacketHost.create("h1")
  h2 = GetPacketHost.create("h2")

  s1 = sim.config.default_switch_type.create('s1')
  s2 = sim.config.default_switch_type.create('s2')
  s3 = sim.config.default_switch_type.create('s3')

  h1.linkTo(s1)
  h2.linkTo(s3)

  s1.linkTo(s2)
  s2.linkTo(s3)

  def test_tasklet ():
    yield 10 # Wait five seconds for routing to converge

    api.userlog.debug("Sending test ping 1 (should get there)")
    h1.ping(h2)

    yield 10

    api.userlog.debug("Checking packet trace (should be [s1, s2, s3, h2])")
    expected_trace = [s1, s2, s3, h2]
    if h2.last_ping_trace is None:
        api.userlog.debug("no ping aarived at h2, cannot check trace.")
        sys.exit(0)
    elif h2.last_ping_trace == expected_trace:
        api.userlog.debug("trace is correct!")
    else:
        api.userlog.debug("trace is incorrect! shoulde be [s1, s2, s3, h2], but is:")
        api.userlog.debug(", ".join([d.name for d in h2.last_ping_trace]))
        sys.exit(0)

    yield 10

    api.userlog.debug("Connecting s1 and s3")
    s1.linkTo(s3)

    yield 10

    api.userlog.debug("Sending test ping 2 (should get there)")
    h1.ping(h2)

    yield 10

    api.userlog.debug("Checking packet trace (should be [s1, s3, h2])")
    expected_trace = [s1, s3, h2]
    if h2.last_ping_trace is None:
        api.userlog.debug("no ping aarived at h2, cannot check trace.")
        sys.exit(0)
    elif h2.last_ping_trace == expected_trace:
        api.userlog.debug("trace is correct!")
    else:
        api.userlog.debug("trace is incorrect! shoulde be [s1, s3, h2], but is:")
        api.userlog.debug(", ".join([d.name for d in h2.last_ping_trace]))
        sys.exit(0)

    yield 10

    api.userlog.debug("Disconnecting s1 from s3")
    s1.unlinkTo(s3)

    yield 10

    api.userlog.debug("Sending test ping 2 (should get there)")
    h1.ping(h2)

    yield 10

    api.userlog.debug("Checking packet trace (should be [s1, s2, s3, h2])")
    expected_trace = [s1, s2, s3, h2]
    if h2.last_ping_trace is None:
        api.userlog.debug("no ping aarived at h2, cannot check trace.")
        sys.exit(0)
    elif h2.last_ping_trace == expected_trace:
        api.userlog.debug("trace is correct!")
        api.userlog.debug("Test passed successfully!")
    else:
        api.userlog.debug("trace is incorrect! shoulde be [s1, s2, s3, h2], but is:")
        api.userlog.debug(", ".join([d.name for d in h2.last_ping_trace]))
        sys.exit(0)

    # End the simulation and (if not running in interactive mode) exit.
    sys.exit(0)

  api.run_tasklet(test_tasklet)
