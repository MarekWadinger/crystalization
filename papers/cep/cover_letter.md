# Cover letter (skeleton)

Draft skeleton. Fill the bracketed placeholders after the Phase 4 reframing; every claim must match the final
manuscript.

---

[Date]

To the Editor-in-Chief,
*Control Engineering Practice*

Dear [Editor's name],

We submit the manuscript "[Final title]" by Marek Wadinger, Patrik Valábek, Erika Plšičík Pavlovičová, Ananya Lohani,
Marián Choma and Radoslav Paulen for consideration as a research article in *Control Engineering Practice*.

**Problem.** Operators of an industrial sugar seed pan decide how much seed massecuite to draw into the A pans, when
to raise the boil-up feed and when to discharge, without any online signal of crystal growth; the DCS trends level,
vacuum, temperature, stirrer current and a Brix-scale signal, none of which is a crystal size.

**Contribution.** We design a soft sensor of crystal growth around the closed-circuit camera already installed at the
seed pan's sight glass, and test its estimator in simulation and on first real camera points: a measurement model of the installed camera (gain, sampled layer, detector), an
observability result (the camera alone observes the relative growth rate and the curve shape, and one microscope
sample restores absolute size), and a camera-aided extended Kalman filter with a per-strike validation protocol. On simulated camera signals it
lowers the log-size error at held-out microscope times from 0.310–0.319 to 0.085–0.109 with one anchor, provided the
camera bias stays constant within a strike; this tests the filter, not the camera. On twelve AI-traced real camera points it does no better than the nominal curve. [Real-camera result from the fine-tuned detector and the
comparison with a process-signal estimator (needs DCS data for 2026-10-30), to be added after the results freeze on
2026-11-23.]

**Fit with the journal.** The paper builds a state estimator on a sensor that is already installed in an industrial
plant, states what it can and cannot observe, and defines a validation protocol on plant data against microscope samples and a
process-signal baseline; the validation itself is pending. This is the scope of *Control Engineering Practice*. [Confirm once the real-camera and
baseline results exist; see `CLAIM_CHANGES.md`.]

**Data and code.** [Zenodo DOI to be added.]

[To confirm at submission: The manuscript is original, has not been published, and is not under consideration
elsewhere. All authors have approved the submitted version.] [Competing interests statement to be confirmed by all authors.] [Generative AI use is
declared in the manuscript.]

[Optional: suggested reviewers, with affiliation and e-mail, and the reason for each.]

Yours sincerely,

Marek Wadinger (corresponding author)
Slovak University of Technology in Bratislava
<marek.wadinger@stuba.sk>
