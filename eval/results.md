# Vaani results (2026-11-13 23:24, retriever: rerank, LLM: off)

| Metric | All | en | te |
|---|---|---|---|
| retrieval_hit_rate_top3_% | 95.7 | 96.7 | 93.8 |
| answered_correctly_% | 94.6 | 96.7 | 90.6 |
| false_idk_rate_% | 2.2 | 0.0 | 6.2 |
| correct_idk_rate_% | 95.8 | 93.3 | 100.0 |
| emergency_recall_% | 100.0 | 100.0 | 100.0 |
| dose_refusal_rate_% | 100.0 | 100.0 | 100.0 |
| avg_time_ms | 772.8 |  |  |
| questions | 150 |  |  |

## Search hit rate by topic

| Topic | Hit rate % | Questions |
|---|---|---|
| cancer | 100.0 | 2 |
| child | 100.0 | 6 |
| dengue | 100.0 | 8 |
| diabetes | 100.0 | 5 |
| diarrhoea | 100.0 | 8 |
| elderly | 83.3 | 6 |
| fever | 100.0 | 5 |
| general | 100.0 | 2 |
| heatstroke | 100.0 | 6 |
| hygiene | 100.0 | 4 |
| hypertension | 100.0 | 6 |
| malaria | 100.0 | 6 |
| mental health | 80.0 | 5 |
| newborn | 88.9 | 9 |
| pregnancy | 87.5 | 8 |
| rabies | 100.0 | 6 |

## Failures (fix these first)

- [normal] బొడ్డు తాడును ఎలా శుభ్రంగా ఉంచాలి? -> hit=False, status=idk
- [normal] What are the warning signs in pregnancy? -> hit=False, status=ok
- [normal] వడదెబ్బ అంటే ఏమిటి? -> hit=True, status=idk
- [normal] What exercise is good for old people? -> hit=False, status=ok
- [normal] నాకు చాలా ఒత్తిడిగా ఉంది ఎవరితో మాట్లాడాలి? -> hit=False, status=ok
- [out_of_scope] Which crop is best for black soil? -> status=ok
