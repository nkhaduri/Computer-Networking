"""
Tests that packets take the lowest-cost path that is the freshest.

                h2
              0 ||
                R4
              //||\\
       c1 2 //  ||  \\ 7 c4
          //   9||    \\
    0   //  6   ||   1  \\   0
h5 --- R1 ----- h1 ----- R2 --- h4
        \\      ||      //
          \\   5||    //
       c2 2 \\  ||  // 2 c3
              \\||//
                R3
             .5 ||
                h3

After routes have converged, sends a packet from h2, h3, h4, and h5 to h2.
The test passes if the packet takes the path that is through R1, R2, and R3,
which has more hops but a lower total cost. We check which path the packet took
using c1, c2, c3, and c4, which are CountingHubs.

The paths that should be taken for this iteration are as follows:

h2 - R4 - R1 - R3 - R2 - h1    total latency = 7
h3 - R3 - R2 - h1              total latency = 3.5
h4 - R2 - h1                   total latency = 1
h5 - R1 - R3 - R2 - h1         total latency = 5

We then diconnect R2 from the graph, and mak sure that the shortest paths are
taken again.

                h2
              0 ||
                R4
              //||
       c1 2 //  ||
          //   9||
    0   //  6   ||   1       0
h5 --- R1 ----- h1 ----- R2 --- h4
        \\      ||
          \\   4||
       c2 2 \\  ||
              \\||
                R3
             .5 ||
                h3

After routes have converged, sends a packet from h2, h3, h4, and h5 to h2.
The test passes if the packet takes the path that is through R1, R2, and R3,
which has more hops but a lower total cost. We check which path the packet took
using c1, c2, c3, and c4, which are CountingHubs.

The paths that should be taken for this iteration are as follows:

h2 - R4 - R1 - h1              total latency = 7
h3 - R3 - h1                   total latency = 4.5
h5 - R1 - h1                   total latency = 5

"""

import sim
import sim.api as api
import sim.basics as basics

from tests.test_simple import GetPacketHost, NoPacketHost


class CountingHub(api.Entity):
    pings = 0

    def handle_rx(self, packet, in_port):
        self.send(packet, in_port, flood=True)
        if isinstance(packet, basics.Ping):
            api.userlog.debug('%s saw a ping' % (self.name, ))
            self.pings += 1


def launch():
    h1 = GetPacketHost.create('h1')
    h2 = NoPacketHost.create('h2')
    h3 = NoPacketHost.create('h3')
    h4 = NoPacketHost.create('h4')
    h5 = NoPacketHost.create('h5')
    r1 = sim.config.default_switch_type.create('r1')
    r2 = sim.config.default_switch_type.create('r2')
    r3 = sim.config.default_switch_type.create('r3')
    r4 = sim.config.default_switch_type.create('r4')
    c1 = CountingHub.create('c1')
    c2 = CountingHub.create('c2')
    c3 = CountingHub.create('c3')
    c4 = CountingHub.create('c4')
    h1.linkTo(r1, latency=6)
    h1.linkTo(r2, latency=1)
    h1.linkTo(r3, latency=5)
    h1.linkTo(r4, latency=9)
    h2.linkTo(r4, latency=0)
    h3.linkTo(r3, latency=.5)
    h4.linkTo(r2, latency=0)
    h5.linkTo(r1, latency=0)
    r4.linkTo(c1, latency=2)
    c1.linkTo(r1, latency=2)
    r1.linkTo(c2, latency=2)
    c2.linkTo(r3, latency=2)
    r3.linkTo(c3, latency=1)
    c3.linkTo(r2, latency=2)
    r2.linkTo(c4, latency=7)
    c4.linkTo(r4, latency=7)

    def test_tasklet():
        yield 20

        api.userlog.debug('Sending pings')
        h2.ping(h1)
        h3.ping(h1)
        h4.ping(h1)
        h5.ping(h1)

        yield 15

        good = True
        if c1.pings == 1 and c2.pings == 2 and c3.pings == 3 and c4.pings == 0 and h1.pings == 4:
            api.userlog.debug('The ping took the right path')
        else:
            api.userlog.error('Something strange happened to the ping')
            good = False

        api.userlog.debug('Disconnecting R2')
        r2.unlinkTo(h1)
        r2.unlinkTo(c4)
        r2.unlinkTo(c3)

        yield 20

        api.userlog.debug('Sending pings')
        h2.ping(h1)
        h3.ping(h1)
        h5.ping(h1)

        yield 15

        if c1.pings == 2 and c2.pings == 2 and c3.pings == 3 and c4.pings == 0 and h1.pings == 7:
            api.userlog.debug('The ping took the right path')
        else:
            api.userlog.debug(c1.pings)
            api.userlog.debug(c2.pings)
            api.userlog.debug(c3.pings)
            api.userlog.debug(c4.pings)
            api.userlog.debug(h1.pings)

            api.userlog.error('Something strange happened to the ping')
            good = False

        import sys
        sys.exit(0 if good else 1)

    api.run_tasklet(test_tasklet)
