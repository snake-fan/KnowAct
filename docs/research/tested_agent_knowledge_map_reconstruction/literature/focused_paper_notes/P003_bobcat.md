# P003 — [BOBCAT](https://www.ijcai.org/proceedings/2021/332)

**Ghosh and Lan, IJCAI 2021. Reading depth: D2.**

## Contribution

Learns adaptive item selection through bilevel optimization and evaluates how quickly methods recover
predictive ability across five real student-response datasets.

## KnowAct transfer

Separate the target policy from the response model, compare against heuristic policies, and report
quality at matched budgets rather than only a final fixed-length score.

## Do not transfer

A fixed calibrated item bank, binary responses, and abundant historical data are substantially easier
than cold-start, open-ended question generation.
