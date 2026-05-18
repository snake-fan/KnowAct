# KnowAct

[中文版本](README.zh-CN.md)

**KnowAct: Evaluating Functional Theory of Mind in Knowledge-Grounded Human-AI Interaction**

KnowAct is a research-oriented benchmark and evaluation framework for studying how AI agents use Theory of Mind-like abilities during knowledge-grounded human-AI interaction.

Instead of only asking whether a model can describe a user's mental state, KnowAct focuses on a more functional question:

> Can an agent use its model of the user to make better interaction decisions?

The project explores how an agent infers, updates, and acts upon a user's knowledge state during multi-turn interaction.

---

## Motivation

Large language model agents are increasingly expected to collaborate with users in open-ended tasks such as learning, research, writing, and decision-making. In these scenarios, a useful agent should not only understand the external task, but also reason about the user's internal state:

- What does the user already know?
- What concepts are missing or misunderstood?
- What should the agent ask next?
- When should the agent explain, challenge, summarize, or move forward?
- How should the agent adapt its behavior based on the user's knowledge profile?

This ability is related to **Theory of Mind**, but KnowAct emphasizes its practical role in interaction. We call this direction **Functional Theory of Mind**: the ability to use user-state reasoning to guide actions in a dialogue.

---

## Core Research Question

KnowAct investigates the following question:

> How can we evaluate whether an AI agent can use Theory of Mind-like user modeling to guide interaction decisions in knowledge-grounded tasks?

More specifically, the project asks:

1. Can an agent infer a user's hidden knowledge profile through limited interaction?
2. Can the agent choose useful conversational actions based on that inferred profile?
3. Can we quantitatively compare the agent's reconstructed user profile with a ground-truth profile?
4. Does a ToM-aware agent loop outperform simpler baselines in profile reconstruction and interaction quality?

---

## Key Idea

KnowAct constructs controlled user profiles and tests whether an agent can recover and use them through dialogue.

The basic evaluation pipeline is:

```text
Ground-truth Knowledge Profile
        ↓
User Simulator
        ↓
Multi-turn Interaction
        ↓
Tested Agent infers User Profile
        ↓
Profile Comparison / Scoring
```

The ground-truth user profile is hidden from the tested agent. The agent must interact with a simulated user, ask questions, interpret responses, and gradually reconstruct the user's knowledge state.

---

## Benchmark Design

KnowAct uses a semi-synthetic benchmark construction process:

1. **Static User Profile Generation**

   LLMs are used to generate initial user profiles, including the user's background, known concepts, missing concepts, misconceptions, preferences, and task goals.

2. **Human Verification**

   Generated profiles are manually checked and revised to ensure consistency, plausibility, and evaluability.

3. **User Simulation**

   An LLM-based user simulator is conditioned on the static profile and plays the role of the user during interaction.

4. **Agent Interaction**

   The tested agent interacts with the simulated user without access to the hidden profile.

5. **Profile Reconstruction**

   After or during the conversation, the tested agent produces an inferred user profile or knowledge map.

6. **Evaluation**

   The inferred profile is compared against the ground-truth profile using quantitative and qualitative metrics.

---

## Knowledge Map

A central object in KnowAct is the **Knowledge Map**.

A knowledge map represents the user's state over a set of concepts, relations, and knowledge attributes.

A possible structure is:

```json
{
  "concepts": [
    {
      "name": "RAG",
      "status": "known",
      "confidence": 0.85,
      "evidence": "User correctly explained retrieval-augmented generation."
    },
    {
      "name": "Theory of Mind",
      "status": "partial",
      "confidence": 0.55,
      "evidence": "User understands mental-state modeling but not evaluation design."
    },
    {
      "name": "KL Divergence",
      "status": "unknown",
      "confidence": 0.30,
      "evidence": "User asked for clarification about distribution comparison."
    }
  ],
  "relations": [
    {
      "source": "User Modeling",
      "target": "Theory of Mind",
      "relation": "related_to"
    },
    {
      "source": "Knowledge Map",
      "target": "Profile Reconstruction",
      "relation": "used_for"
    }
  ]
}
```

The knowledge map can support both evaluation and agent decision-making.

---

## Evaluation

KnowAct evaluates agents along several dimensions.

### 1. Profile Reconstruction Accuracy

The agent's inferred profile is compared with the ground-truth profile.

Possible metrics include:

* KL divergence between profile distributions
* Concept-level precision, recall, and F1
* Misconception detection accuracy
* Graph similarity between knowledge maps
* Calibration error of confidence scores
* Attribute-level matching accuracy

### 2. Interaction Efficiency

The agent should recover useful information with limited interaction.

Possible metrics include:

* Number of turns used
* Information gain per turn
* Redundant question rate
* Coverage of important profile dimensions
* Early-stage reconstruction quality

### 3. Action Quality

The benchmark also evaluates whether the agent uses the inferred profile to make better decisions.

Possible action types include:

* Ask a diagnostic question
* Explain a missing concept
* Verify an uncertain belief
* Challenge a misconception
* Summarize the user's current understanding
* Recommend the next learning step

The goal is not only to infer the user's state, but to act appropriately based on that state.

---

## Agent Loop

KnowAct includes a planned ToM-aware agent loop.

A simplified version:

```text
Observe user response
        ↓
Update inferred knowledge map
        ↓
Estimate uncertainty
        ↓
Select next interaction action
        ↓
Generate response
        ↓
Continue interaction
```

The agent loop explicitly separates:

* user-state inference
* uncertainty estimation
* action selection
* response generation
* profile reconstruction

This makes it possible to compare different agent designs and analyze where failures occur.

---

## Baselines

KnowAct is designed to compare a ToM-aware agent with simpler baselines, such as:

### Direct Chat Baseline

The model chats with the user normally and produces a final profile after the conversation.

### Passive Summarization Baseline

The model summarizes the user's knowledge state based only on observed dialogue, without actively choosing diagnostic questions.

### Fixed-Question Baseline

The agent follows a predefined questionnaire and does not adapt its questions based on previous answers.

### Random Action Baseline

The agent randomly selects from available interaction actions.

### Oracle Profile Baseline

The agent has access to the ground-truth profile. This serves as an upper-bound reference for action quality.

---

## Research Hypothesis

KnowAct is based on the hypothesis that:

> Agents with explicit user modeling and ToM-like action selection should infer user knowledge states more accurately and interact more efficiently than agents without such mechanisms.

This project tests whether that hypothesis holds under controlled knowledge-grounded interaction settings.

---

## Current Status

KnowAct is currently in the design and prototyping stage.

Implemented / planned components include:

- [ ] User profile schema
- [ ] Knowledge map representation
- [ ] LLM-based profile generation
- [ ] Human verification protocol
- [ ] User simulator
- [ ] Tested agent interface
- [ ] ToM-aware agent loop
- [ ] Baseline agents
- [ ] Profile comparison metrics
- [ ] Evaluation scripts
- [ ] Experiment reports

---

## Example Task Setting

A possible benchmark scenario:

```text
Domain: Research paper reading

Ground-truth user profile:
- Understands basic LLM concepts
- Has partial knowledge of RAG
- Does not fully understand Theory of Mind
- Confuses user modeling with personalization
- Wants to design a research project around AI-assisted paper reading

Agent goal:
- Interact with the user
- Infer the user's knowledge state
- Identify missing concepts and misconceptions
- Build a reconstructed knowledge map
- Choose helpful next actions
```

The agent is evaluated by how closely its reconstructed profile matches the hidden ground-truth profile and how effectively it uses that profile during the conversation.

---

## Why KnowAct?

Existing evaluations often test whether a model can answer questions about beliefs, intentions, or hidden states. KnowAct instead focuses on whether a model can use such reasoning in interaction.

The project shifts the evaluation focus from:

```text
Can the model describe the user's mental state?
```

to:

```text
Can the model act better because it models the user's mental state?
```

This makes KnowAct especially relevant for educational agents, research assistants, personalized AI systems, and knowledge-grounded collaborative agents.

---

## Roadmap

Future directions include:

- Designing richer knowledge map structures
- Creating multiple domains beyond paper reading
- Adding controlled misconceptions to user profiles
- Measuring active information-seeking behavior
- Comparing different agent architectures
- Studying failure modes in user simulation
- Reducing circularity between profile generation, simulation, and evaluation
- Testing with real human users after synthetic validation

---

## Citation

This project is under active development. Citation information will be added later.
