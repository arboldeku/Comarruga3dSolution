# Defending Comarruga Flood Lab: guidelines and pitches

All figures are preliminary estimates from a simplified, uncalibrated model (source: `results/kpis_summary.json`, 10 Nov 2026). Say so out loud at least once.

## 1. Guidelines

**The one sentence to land**
"We built a what-if flood simulator on the real terrain of Coma-ruga, and we used it to measure a decision AI against physics before trusting it."

**Do**
- Open with the question a neighbour would ask: "If it rains this much and we build that, how many centimetres of water do I save on my street?"
- Show the demo early. Terrain, 100 mm rain, before/after, difference map. Thirty seconds, no narration of menus.
- State the Jev result plainly and first-hand: 0 of 24 correct. Then explain why that is the finding, not the embarrassment.
- Separate three things every time: what is **observed** (terrain, buildings, rain totals), what is **modelled** (depths), what is **assumed** (land use, rain duration, tank location, no sewers).
- Give numbers with their unit and condition: "with 100 mm in 60 minutes".
- Finish with the next concrete step, not a vision.

**Don't**
- Don't say the Riuet works caused the flooding. It is one hypothesis among several (saturated drainage, sea level, sediment, rain intensity).
- Don't say the announced 3,500 m³ tank "doesn't work". In our model it was placed by assumption and barely filled; that says nothing about the real project.
- Don't quote the 1–2 m depths as expected street flooding. The model has no sewer network; they are an upper bound.
- Don't present permeable pavement as the winner. Its advantage is inflated by missing land-use data.
- Don't call the model calibrated, validated or a digital twin. It is an exploratory tool.

**Likely questions and short answers**

| Question | Answer |
|---|---|
| Is the terrain real? | Yes: ICGC 5 m elevation model, 1 km² of Brisamar, plus ICGC orthophoto and 2,013 Catastro building volumes. Buildings are visual only. |
| Is the rain real? | The totals are documented (100 mm on 22 Aug 2026, municipal statement; about 60 mm on 2 Nov, press, unverified). The 60-minute duration is an assumption; we have no hyetograph yet. |
| Why did Jev fail? | It decided blind: a handful of features per hotspot, no examples, and it picked the storage tank every time. In the model that tank barely fills. |
| So was Jev useless? | It was fast (392 ms median) and cheap (about 0.000034 USD per decision). It was not accurate for this task. We know that because we ran it in shadow mode against the solver with a deterministic fallback. |
| What would make Jev useful here? | Examples labelled by the solver, richer context, and a task of judgement rather than physics, such as triaging neighbour reports. Always compared against a simple rule. |
| Can a council use this today? | No. It needs the drainage network, real rain series, calibration against observed depths and review by a hydraulic engineer. |
| What is the mass balance? | Rain in equals water stored, infiltrated and drained, within 1.05% at worst. The acceptance limit was 5%. |
| How long did it take? | Two short sessions in one day, from an empty repository. |

**Delivery**
- Slow down on numbers. One number per sentence.
- If the demo fails, switch to the slides; the KPIs are in `docs/Comarruga_Flood_Lab_KPIs.pptx`.
- If you don't know, say "we don't have that data yet" and name who holds it.

## 2. Elevator pitch (60 seconds, about 150 words)

In Coma-ruga, on the Catalan coast, a hundred millimetres of rain fell on the 22nd of August and flooded garages and ground floors. The council announced a storage tank. Nobody can yet answer a neighbour's simple question: if it rains this much and we build that, how much water do I save on my street?

In one day we built a simulator that starts to answer it. It runs on the real terrain of the Brisamar district, using public elevation data, and compares four interventions under the same storm, in 3D, in a browser.

We also had to use Jev, a decision AI. We let it pick the best intervention for each flood hotspot, in shadow mode, and checked it against the physics. It answered in under half a second, for a fraction of a cent. It got zero out of twenty-four right.

That is our result: a tool that measures an AI's judgement before anyone acts on it.

## 3. Full pitch (4–5 minutes, about 650 words)

**The problem (40 seconds)**

Coma-ruga is a low, flat seaside district in El Vendrell. On the 22nd of August 2026 the council reported a hundred millimetres of rain there. Cars, garages and ground floors flooded. It happened again in November. The author of this project lives there; by his own account, water entered his home once in twenty-seven years and twice this year. That is testimony, not yet verified.

The council has announced a 3,500 cubic metre tank and new drains, at over four million euros. Neighbours and engineers are debating whether it is enough. What is missing is a shared, visual way to ask: under the same storm, what does each option actually change?

**What we built (60 seconds)**

A what-if simulator with three parts, each doing one job.

A physics solver calculates water depth. We did not write one; we used Landlab, an established scientific library, and wrapped it with rainfall, infiltration and a mass-balance check.

A decision model, Jev, chooses the best intervention for each flood hotspot and gives a probability. It never does the hydraulics.

A 3D viewer in the browser shows before, after and the difference.

It runs on real public data: the ICGC five-metre elevation model for one square kilometre of Brisamar, the ICGC orthophoto, and 2,013 building volumes from the Catastro. We simulate three rainfalls, including the documented hundred millimetres, across the current situation and four interventions: widening the channel, a storage tank, permeable pavement and raised kerbs. Fifteen simulations, all conserving water within about one percent.

**Demo (45 seconds)**

Here is Brisamar. I select a hundred millimetres. This is the current situation: about 23 percent of the area under more than five centimetres of water. Now I widen the channel. Green is where water drops, by seven to fourteen centimetres across the low area. The flooded surface falls by 12.6 percent. The channel itself carries more water, which is the intention.

**A problem we solved (60 seconds)**

Our first version reported that widening the channel cut the maximum depth by 27 centimetres. It looked great. Then our auditor agent, whose only job is to try to break our conclusions, recomputed it. That maximum was inside the channel. On the streets, the saving was half a centimetre, and with heavier rain two of our interventions made the urban maximum worse.

The numbers were correct and the headline was misleading. So we changed the metric: every result now reports depth in the urban area, separately from the channel, and the viewer and the deck flag any intervention that makes things worse. We would rather show a smaller true number than a larger flattering one.

**Jev's role (60 seconds)**

Jev was a requirement, so we tested it properly. For each of eight hotspots and three rainfalls we asked it to choose the best intervention, in shadow mode: it decides, we log it, nothing acts on it. A simple deterministic rule runs alongside as a fallback and a baseline.

Jev answered all twenty-four calls, with a median latency of 392 milliseconds, at roughly 0.000034 dollars each. It chose the storage tank every single time, and it was right zero times. The simple rule scored 4.2 percent. Always answering "permeable pavement" would have scored 79.2 percent.

Why? Jev decided blind, from a few terrain features and no examples, on a question that is really physics. So its role today is negative on accuracy and positive on speed and cost. The valuable part is that we caught it by design.

**Honest limits and next steps (35 seconds)**

This model is not calibrated. It has no sewer network, so depths are an upper bound. Land use and rain duration are assumptions, and the tank location is ours, not the council's.

Next: real rainfall series from Meteocat, the drainage inventory from the water utility, one-metre terrain with buildings as obstacles, and calibration against flood marks photographed by neighbours. Then a proper decision layer, and review by a hydraulic engineer.

We did not draw a flood. We connected public data to a physical model, and we measured an AI against it before believing it.
