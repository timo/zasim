import zasim
import sys

ca_init, display_init, histogram_init = sys.argv[1:]

if ca_init == "constructor":
    binrule = zasim.ca.BinRule(
            rule = 110,
            initial = zasim.conf.RandomConfiguration)
    # this API must support setting the size manually and then initializing it
    # from random data, zeros, ones, whatever as well as initializing it from
    # a file
    binrule.size = 300
    binrule.init()
elif ca_init == "properties":
    binRule = zasim.ca.BinRule()
    # several attributes would actually be properties with getters and setters
    binrule.rule = 110
    binrule.size = (400,)
    binrule.init(zasim.conf.RandomConfiguration)

if display_init == "constructor":
    binrule_display = zasim.display.HistoryDisplay(
            ca=binrule,
            lines=300,
            scale=2)
elif display_init == "properties":
    binrule_display = zasim.display.HistoryDisplay()
    binrule_display.ca = binrule
    binrule_display.size = (800, 600)
elif display_init == "strange":
    # maybe it would be nice if the different ca classes knew what kind of display
    # is right for them
    binrule_display = binrule.create_display(800, 600)

if histogram_init == "one_zero_distribution":
    histogram = zasim.histogram.DistributionDisplay(binrule)
elif histogram_init == "activity_history":
    histogram = zasim.histogram.ActivityHistoryDisplay(binrule)
elif histogram_init == "distribution_history":
    histogram = zasim.histogram.DistributionHistoryDisplay(binrule)

histogram.show()

# open up the window
binrule_display.show()

# step once
# also update all guis related
binrule.step()

# do ten steps, update the gui as fast as possible
binrule.step(10)

# fast-forward 1000 steps without updating the gui
binrule.fast_step(1000)

# let the gui drive the stepping with delays
binrule_display.animate_steps(steps=1000, delay=0.01)

# why not also let the user say for how long it should animate?
binrule_display.animate_steps(steps=1000, time=10)

# displays should be able to save out images
binrule_display.screenshot("pretty.png")

# cas should be able to snapshot configurations or clone themselves
snap1 = binrule.snapshot()

binrule.step(100)
binrule.restore(snap1)

# maybe something like this is interesting
_snaps = []
def step_hook(ca):
    _snaps.append(ca.snapshot())
binrule.step_hook(step_hook)
binrule.step(100)
binrule.step_hook(None)

# comparing configurations of different automatons - as long as they are
# comparable at all - is pretty neat, i suppose.
other_ca = binrule.shallow_clone()

# manipulation of cells should be possible from the gui as well as the shell
other_ca[10:15] = [0, 1, 0, 1, 1]

other_ca.step(100)
binrule.step(100)

# displaying a comparison between two configurations might work like this
diff = other_ca.diff(binrule)
diff_disp = zasim.display.DiffDisplay(diff)


# TODO zellularautomat game of life
# TODO moebius-bandtransformation
# TODO beliebige waende aneinanderkopieren


# 1. qt geschwindigkeit untersuchen: 1x1 pixel pro feld, 3x3 pixel, bilder
#    1d automat mit history, 2d automat (game of life z.B.)
# 2. vision implementieren
