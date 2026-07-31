# Experiment 03 Materials

[中文](README.zh-CN.md)

The experiment design is ready, but formal materials are intentionally not
frozen yet. Code execution must wait for the following versioned inputs:

- reviewed graph versions that passed Experiment 01 or an explicitly reported
  alternative review gate;
- reviewed hidden Knowledge Maps with planned mastery strata;
- simulator version and validity status from Experiment 02;
- immutable Episode Manifest registrations for every paired condition;
- tested-agent provider, model, temperature, retry policy, and prompt/code
  revision;
- simulator provider, model, condition, and repeated-seed policy;
- turn budgets and episode exclusion rules;
- a versioned expert question bank before fixed, random, coverage-greedy, or
  LLM bank-selection baselines are treated as formal runtime kinds;
- an analysis manifest naming primary contrasts, bootstrap blocks, multiplicity
  correction, failure handling, and the pilot/final split.

Engineering smoke-test manifests must be marked `development` and must not be
mixed into the confirmatory result set.
