# What do the nearest FSD50K clips actually sound like?

Post hoc and descriptive. No gate reads this file.

## Why a number cannot close this

Every distance here is between log-mel *spectra* of RMS-normalised audio. That
throws away level, phase and all temporal structure above the frame rate, which
is most of what makes a sound recognisable. Two recordings can sit close in this
space and be obviously different things to a listener - broadband hiss from a
crowd, a hairdryer and rain on water are near neighbours by LTAS and nobody
confuses them by ear. The measurement can therefore show that nothing in the
FSD50K training pool is acoustically close to MarVEN noise, which is a real
result and the one the paper needs; it cannot show that something close-by
*sounds marine*. Only listening settles that, and only listening can catch the
case the reviewer is really asking about: an unlabelled clip that a human would
call rain or a boat.

**The lines below are Rana's to fill in.** Each one names the clip, its FSD50K
labels and its measured distance; the `heard:` field is deliberately empty. The
cached 16 kHz audio is at
`C:\Users\ranar\Downloads\MAIN-failure-direction(ALL)\Failure-Direction-Datasets\FSD50K (dataset)\fsd16k/<split>/<fname>.wav`.

## Reference points, for reading the distances

- positive control, DeepShip ship vs MarVEN large_commercial_ship, pooled: LTAS 8.29 dB, FD 5570.1
- the same control at per-crop scale, nearest 10 s crop: LTAS 3.86 dB
- calibration, MarVEN type against MarVEN type:
  - rainfall vs hurricane: LTAS 29.51 dB, FD 56422.9
  - rainfall vs lightning: LTAS 11.17 dB, FD 9573.0
  - large_commercial_ship vs bubble_curtain: LTAS 23.28 dB, FD 35350.0

A nearest FSD50K clip farther than the positive control means the pool holds
nothing as close to that MarVEN type as a genuine recording of the same class.

### Read the per-clip column against the marine reference, not the control

The nearest training clip is a minimum over ~29,850 candidates; the DeepShip
control and the calibration pairs are single unselected pairs. An extreme-order
statistic will beat an unselected one whatever the corpora are really like, so
`fsd_nearest_clip` being below `control_per_crop_nearest` on its own says
nothing. The rows that are comparable are FSD50K's own held-out marine-labelled
clips, `fsd_weather_*` and `fsd_boat_*` in summary.csv - same per-clip scale,
same minimum-over-a-pool construction, and they are labelled rain, thunder,
wind and boat, so they are what a marine-like FSD50K clip actually measures:

- rainfall: nearest held-out fsd_weather clip 9.57 dB vs nearest TRAINING clip 5.81 dB
- lightning: nearest held-out fsd_weather clip 3.83 dB vs nearest TRAINING clip 3.19 dB
- hurricane: nearest held-out fsd_weather clip 4.01 dB vs nearest TRAINING clip 2.61 dB
- bubble_curtain: nearest held-out fsd_weather clip 4.41 dB vs nearest TRAINING clip 3.82 dB
- large_commercial_ship: nearest held-out fsd_weather clip 3.92 dB vs nearest TRAINING clip 2.83 dB
- rainfall: nearest held-out fsd_boat clip 11.46 dB vs nearest TRAINING clip 5.81 dB
- lightning: nearest held-out fsd_boat clip 5.48 dB vs nearest TRAINING clip 3.19 dB
- hurricane: nearest held-out fsd_boat clip 7.45 dB vs nearest TRAINING clip 2.61 dB
- bubble_curtain: nearest held-out fsd_boat clip 7.39 dB vs nearest TRAINING clip 3.82 dB
- large_commercial_ship: nearest held-out fsd_boat clip 3.71 dB vs nearest TRAINING clip 2.83 dB

If the training clips are not clearly farther than the marine-labelled ones,
the honest conclusion is about the measurement: a 64-band LTAS cannot separate
marine from non-marine inside FSD50K, so it can neither support nor refute the
paper's claim, and the claim should keep resting on the labels while saying so.

## What this run found

On the per-clip LTAS scale the nearest TRAINING clip is closer to the MarVEN type than ANY held-out marine-labelled clip for **5 of 5** types (rainfall, lightning, hurricane, bubble_curtain, large_commercial_ship). So the measurement does not separate marine from non-marine here, and the leaf labels
of those nearest clips say why:

- **rainfall**: nearest training clips are `Breathing`, `Church_bell`, `Fixed-wing_aircraft_and_airplane`, `Guitar`, `Scratching_(performance_technique)`
- **lightning**: nearest training clips are `Knock`, `Scratching_(performance_technique)`, `Fixed-wing_aircraft_and_airplane`, `Gunshot_and_gunfire`, `Fireworks`
- **hurricane**: nearest training clips are `Knock`, `Knock`, `Knock`, `Knock`, `Boom`
- **bubble_curtain**: nearest training clips are `Motor_vehicle_(road)`, `Hi-hat`, `Zipper_(clothing)`, `Telephone`, `Knock`
- **large_commercial_ship**: nearest training clips are `Subway_and_metro_and_underground`, `Accelerating_and_revving_and_vroom`, `Train`, `Bus`, `Subway_and_metro_and_underground`

Breathing, a church bell, a piano and a door knock are not rain, thunder or a
ship, and no listener would confuse them. A 64-band LTAS ranks them ahead of
FSD50K's own labelled rain and thunder clips, so on this evidence the acoustic
check **cannot support the paper's claim and cannot refute it either**. The
claim should keep resting on the labels, and the Limitations sentence should
say that an acoustic check was run and was uninformative rather than claim it
passed.

One substantive exception is worth a sentence in its own right. For
`large_commercial_ship` the nearest training clips are machinery - subway, train, bus,
engine, aircraft - and the nearest labelled `fsd_boat` clip sits right among
them rather than below them. MarVEN ship noise IS engine noise, and
`EXCLUDE_MARINE` removed the `Boat_and_Water_vehicle` label but not `Train`,
`Engine`, `Subway_and_metro_and_underground` or `Motor_vehicle_(road)`. So for
the ship type the training pool does contain spectrally adjacent broadband
machinery, and 'never saw marine noise' is a statement about labels, not about
what the models heard. For the four weather and bubble-curtain types the nearest
neighbours are incidental and unrelated, so there the unseen framing is safe on
semantics even though LTAS cannot certify it.

## The five nearest clips per MarVEN type

### rainfall

- **rank 1, clip 26335** (dev), LTAS 5.81 dB, 124 frames
  - labels: `Breathing,Respiratory_sounds`
  - heard: _(to fill in)_
- **rank 2, clip 318599** (dev), LTAS 6.75 dB, 417 frames
  - labels: `Church_bell,Bell`
  - heard: _(to fill in)_
- **rank 3, clip 263961** (dev), LTAS 6.76 dB, 276 frames
  - labels: `Fixed-wing_aircraft_and_airplane,Aircraft,Vehicle`
  - heard: _(to fill in)_
- **rank 4, clip 16056** (dev), LTAS 6.91 dB, 233 frames
  - labels: `Guitar,Plucked_string_instrument,Musical_instrument,Music`
  - heard: _(to fill in)_
- **rank 5, clip 61914** (dev), LTAS 6.97 dB, 21 frames
  - labels: `Scratching_(performance_technique),Musical_instrument,Music`
  - heard: _(to fill in)_

### lightning

- **rank 1, clip 364680** (dev), LTAS 3.19 dB, 84 frames
  - labels: `Knock,Door,Wood,Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_
- **rank 2, clip 61879** (dev), LTAS 3.44 dB, 67 frames
  - labels: `Scratching_(performance_technique),Musical_instrument,Music`
  - heard: _(to fill in)_
- **rank 3, clip 263960** (dev), LTAS 3.55 dB, 322 frames
  - labels: `Fixed-wing_aircraft_and_airplane,Aircraft,Vehicle`
  - heard: _(to fill in)_
- **rank 4, clip 158977** (dev), LTAS 3.79 dB, 59 frames
  - labels: `Gunshot_and_gunfire,Explosion`
  - heard: _(to fill in)_
- **rank 5, clip 368416** (dev), LTAS 3.80 dB, 361 frames
  - labels: `Fireworks,Explosion`
  - heard: _(to fill in)_

### hurricane

- **rank 1, clip 336391** (dev), LTAS 2.61 dB, 80 frames
  - labels: `Knock,Door,Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_
- **rank 2, clip 104000** (dev), LTAS 2.85 dB, 40 frames
  - labels: `Knock,Door,Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_
- **rank 3, clip 103999** (dev), LTAS 2.90 dB, 42 frames
  - labels: `Knock,Door,Wood,Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_
- **rank 4, clip 103998** (dev), LTAS 3.14 dB, 77 frames
  - labels: `Knock,Door,Wood,Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_
- **rank 5, clip 102733** (dev), LTAS 3.41 dB, 114 frames
  - labels: `Boom,Explosion`
  - heard: _(to fill in)_

### bubble_curtain

- **rank 1, clip 329624** (dev), LTAS 3.82 dB, 405 frames
  - labels: `Motor_vehicle_(road),Vehicle`
  - heard: _(to fill in)_
- **rank 2, clip 75017** (dev), LTAS 3.95 dB, 18 frames
  - labels: `Hi-hat,Cymbal,Percussion,Musical_instrument,Music`
  - heard: _(to fill in)_
- **rank 3, clip 393457** (dev), LTAS 4.07 dB, 43 frames
  - labels: `Zipper_(clothing),Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_
- **rank 4, clip 201877** (dev), LTAS 4.13 dB, 101 frames
  - labels: `Telephone,Alarm`
  - heard: _(to fill in)_
- **rank 5, clip 182023** (dev), LTAS 4.32 dB, 98 frames
  - labels: `Knock,Door,Domestic_sounds_and_home_sounds`
  - heard: _(to fill in)_

### large_commercial_ship

- **rank 1, clip 187305** (dev), LTAS 2.83 dB, 466 frames
  - labels: `Subway_and_metro_and_underground,Rail_transport,Vehicle`
  - heard: _(to fill in)_
- **rank 2, clip 386948** (dev), LTAS 2.98 dB, 273 frames
  - labels: `Accelerating_and_revving_and_vroom,Engine`
  - heard: _(to fill in)_
- **rank 3, clip 112698** (dev), LTAS 3.17 dB, 341 frames
  - labels: `Train,Rail_transport,Vehicle`
  - heard: _(to fill in)_
- **rank 4, clip 147148** (dev), LTAS 3.19 dB, 261 frames
  - labels: `Bus,Motor_vehicle_(road),Vehicle`
  - heard: _(to fill in)_
- **rank 5, clip 123964** (dev), LTAS 3.19 dB, 211 frames
  - labels: `Subway_and_metro_and_underground,Rail_transport,Vehicle`
  - heard: _(to fill in)_
