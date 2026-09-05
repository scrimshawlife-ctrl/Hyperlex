# 001 addendum — command + agent UX

See spec **002** for the normative command surface.

v0.1 implement already has `python -m hyperlex.mutation`.
T8 on the original task list becomes: wire `$HLX mutation trace` + deprecated `mutation-trace` alias. Do not ship a third spelling as the primary.

Hermes agent default: read `analysis.mutation_trace` off `pipeline` output. Only call the noun CLI when the user asked for operators in isolation or for next-forms.
