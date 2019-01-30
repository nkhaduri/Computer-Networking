"""
Tests that packets take the lowest-cost path.

Creates the following topology

             2 (c1)
          R1 ------- h2
         //        //||
     1 //     1  //  ||
     //        //    || 3 (c5)
    ||   1   ||      ||
    h1 ----- R2      R4
     \\      ||\\ 2  ||
(c6) 3 \\  1 ||  \\  || 3
         \\  ||    \\||
          -- R3 ---- h3
               4 (c3)

Link between R3 and R2 is c4
Link between R2 and h3 is c2

We then send the following pings, which will generate the following paths:
(Note: The hosts do not know which router has the shortest path,
so will send packets to all connected routers)

h1.pings(h2):
    h1 - R1 - (c1) - h2
    h1 - R2 - h2
    h1 - (c6) - R3 - (c4) - R2 - h2

h1.ping(h3):
    h1 - R1 - X
    h1 - R2 - (c2) - h3
    h1 - (c6) - R3 - (c4) - R2 - (c2) - h3

h2.ping(h3):
    h2 - (c1) - R1 - X
    h2 - R2 - (c2) - h3
    h2 - (c5) - R4 - h3

So the counting hubs should have the following ping:
    c1: 2
    c2: 3
    c3: 0
    c4: 2
    c5: 1
    c6: 2

We then change the topology to the following:

             2 (c1)
          R1 ------- h2
         //          ||
     1 //            ||
     //              || 3 (c5)
    ||   1           ||
    h1 ----- R2      R4
     \\      ||      ||
(c6) 3 \\  1 ||      || 3
         \\  ||      ||
          -- R3 ---- h3
               4 (c3)

Link between R3 and R2 is c4

We then send the following pings, which will generate the following paths:

h1.pings(h2):
    h1 - R1 - (c1) - h2
    h1 - R2 - X
    h1 - (c6) - R3 - X

h1.ping(h3):
    h1 - R1 - X
    h1 - R2 - (c4) - R3 - (c3) - h3
    h1 - (c6) - R3 - (c3) - h3

h2.ping(h3):
    h2 - (c1) - R1 - X
    h2 - (c5) - R4 - h3

So the counting hubs should have the following ping:
    c1: += 2 = 4
    c2: += 0 = 3
    c3: += 2 = 2
    c4: += 1 = 3
    c5: += 1 = 2
    c6: += 2 = 4

Then once again, we change the topology to be as follows:

             2 (c1)
          R1 ------- h2
         //          ||
     1 //            ||
     //              || 3 (c5)
    ||   1           ||
    h1 ----- R2      R4
             ||      ||
           1 ||      || 3
             ||      ||
             R3 ---- h3
               4 (c3)

Link between R3 and R2 is c4

We then send the following ping:

h1.pings(h3):
    h1 - R1 - X
    h1 - R2 - (c4) - R3 - (c3) - h3

So the counting hubs should have the following ping:
    c1: += 0 = 4
    c2: += 0 = 3
    c3: += 1 = 3
    c4: += 1 = 4
    c5: += 0 = 2
    c6: += 0 = 4

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
    h1 = NoPacketHost.create('h1')
    h2 = GetPacketHost.create('h2')
    h3 = GetPacketHost.create('h3')
    r1 = sim.config.default_switch_type.create('r1')
    r2 = sim.config.default_switch_type.create('r2')
    r3 = sim.config.default_switch_type.create('r3')
    r4 = sim.config.default_switch_type.create('r4')
    c1 = CountingHub.create('c1')
    c2 = CountingHub.create('c2')
    c3 = CountingHub.create('c3')
    c4 = CountingHub.create('c4')
    c5 = CountingHub.create('c5')
    c6 = CountingHub.create('c6')
    h1.linkTo(r1, latency=1)
    h1.linkTo(r2, latency=1)
    h1.linkTo(c6, latency=3)
    c6.linkTo(r3, latency=3)
    r1.linkTo(c1, latency=2)
    c1.linkTo(h2, latency=2)
    r2.linkTo(h2, latency=1)
    r2.linkTo(c2, latency=2)
    c2.linkTo(h3, latency=2)
    r2.linkTo(c4, latency=1)
    c4.linkTo(r3, latency=1)
    r3.linkTo(c3, latency=4)
    c3.linkTo(h3, latency=4)
    h2.linkTo(c5, latency=3)
    c5.linkTo(r4, latency=3)
    r4.linkTo(h3, latency=2)

    def test_tasklet():
        yield 100

        api.userlog.debug('Sending pings')
        h1.ping(h2)
        h1.ping(h3)
        h2.ping(h3)

        yield 50

        if c1.pings == 2 and c2.pings == 3 and c3.pings == 0 and c4.pings == 2 and c5.pings == 1 and c6.pings == 2:
            api.userlog.debug('The ping took the right path')
            good = True
        else:
            api.userlog.error('Something strange happened to the ping')
            good = False

        api.userlog.debug('Disconnecting R2 to h2')
        r2.unlinkTo(h2)
        api.userlog.debug('Disconnecting R2 to h3')
        r2.unlinkTo(c2)
        c2.unlinkTo(h3)

        yield 25

        api.userlog.debug('Sending pings')
        h1.ping(h2)
        h1.ping(h3)
        h2.ping(h3)

        yield 20

        if c1.pings == 4 and c2.pings == 3 and c3.pings == 2 and c4.pings == 3 and c5.pings == 2 and c6.pings == 4:
            api.userlog.debug('The ping took the right path')
            good = True
        else:
            api.userlog.error('Something strange happened to the ping')
            good = False

        api.userlog.debug('Disconnecting h1 to R3')
        h1.unlinkTo(c6)
        c6.unlinkTo(r3)

        yield 20

        api.userlog.debug('Sending pings')
        h1.ping(h3)

        yield 20

        if c1.pings == 4 and c2.pings == 3 and c3.pings == 3 and c4.pings == 4 and c5.pings == 2 and c6.pings == 4:
            api.userlog.debug('The ping took the right path')
            good = True
        else:
            api.userlog.error('Something strange happened to the ping')
            good = False

        import sys
        sys.exit(0 if good else 1)

    api.run_tasklet(test_tasklet)
