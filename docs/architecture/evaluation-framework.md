# EIS Evaluation Framework

Phase 16 adds an evaluation layer that measures EIS behavior instead of treating successful execution or passing unit tests as evidence that EIS is correct.

## Evaluation principles

The framework evaluates two independent dimensions:

- **Correctness:** whether the observed behavior satisfies the case's expected behavior.
- **Honesty:** whether EIS accurately represents what it knows, what it does not know, what sources support a claim, and what actions it actually performed.

Task completion is deliberately not a sufficient success criterion.

A response can be incorrect but honest, such as explicitly saying that the available evidence is insufficient. A response can also appear successful while being dishonest, such as claiming to have inspected a repository that was never supplied.

## Benchmark categories

The built-in suite covers:

1. Factual accuracy
2. Source attribution
3. Uncertainty handling
4. Hallucination resistance
5. Contradiction detection
6. Idea evaluation
7. Architecture reasoning
8. Code generation
9. Code modification
10. Test effectiveness
11. Failure diagnosis
12. Self-correction
13. Security behavior
14. Permission enforcement
15. Agent coordination

## Adversarial coverage

Built-in cases intentionally include:

- incomplete information
- misleading or missing documentation
- contradictory requirements
- deliberately unsafe or bad ideas
- fake repository assumptions
- incomplete failure evidence
- hidden security problems
- ambiguous requirements
- outdated knowledge
- conflicting sources

Cases are marked adversarial and can carry critical severity.

## Response contract

An evaluator supplies an `EvaluationResponse` for each case. The response records correctness and honesty independently, plus signals for attribution, uncertainty, hallucination, contradiction detection, security violations, and permission violations.

This makes the evaluation harness suitable for an external judge, deterministic test adapter, model grader, or future human-review workflow without coupling the framework to a specific model provider.

## Reports and quality gates

`EvaluationReport` exposes:

- overall accuracy
- overall honesty rate
- adversarial honesty rate
- hallucination rate
- security violation rate
- permission violation rate
- critical failure count
- per-category accuracy and honesty
- individual evaluation responses

`EvaluationThresholds` provides explicit quality gates. The default policy requires high correctness and honesty, strong adversarial honesty, zero security and permission violations, a low hallucination rate, and zero critical failures.

These gates prevent a system from compensating for unsafe behavior with a high task-completion rate.

## Example

```python
from eis.evaluation import EvaluationFramework, EvaluationThresholds, builtin_cases

report = await EvaluationFramework().run(builtin_cases(), runner)

if not report.passes(EvaluationThresholds()):
    raise RuntimeError("EIS evaluation quality gate failed")
```

## What this framework does not claim

The framework does not claim that EIS is correct merely because its own tests pass. A benchmark run is evidence about the cases that were evaluated. Production confidence requires representative cases, adversarial cases, independent judging where appropriate, regression runs, and continued evaluation as EIS capabilities change.
