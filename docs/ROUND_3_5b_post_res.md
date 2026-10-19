# Round 3.5b post-run analysis (res; not a decision input)

## 1. Paired changes relative to d2

| variant | records correct | fixed vs d2 | broken vs d2 | decisions right | fixed vs d2 | broken vs d2 |
|---|---|---|---|---|---|---|
| d2 | 2913/2974 | 0 | 0 | 715/720 | 0 | 0 |
| F1 | 2922/2974 | 9 | 0 | 715/720 | 0 | 0 |
| F2 | 2948/2974 | 35 | 0 | 720/720 | 5 | 0 |
| d3 | 2957/2974 | 44 | 0 | 720/720 | 5 | 0 |

World decisions changed between d2 and d3: giver r35-res-17 A find fixed; giver r35-res-17 B find fixed; giver r35-res-22 A find fixed; giver r35-res-31 A find fixed; giver r35-res-31 B find fixed

## 2. Pair success with Wilson 95% intervals (d3)

| kind:goal | pairs | pair success | interval |
|---|---|---|---|
| giver:find | 40 | 1.000 | [0.912, 1.000] |
| hidden:find | 40 | 1.000 | [0.912, 1.000] |
| moved:find | 40 | 1.000 | [0.912, 1.000] |
| object:current | 40 | 1.000 | [0.912, 1.000] |
| object:first | 40 | 1.000 | [0.912, 1.000] |
| object:previous | 40 | 1.000 | [0.912, 1.000] |
| person:current | 40 | 1.000 | [0.912, 1.000] |
| person:first | 40 | 1.000 | [0.912, 1.000] |
| person:previous | 40 | 1.000 | [0.912, 1.000] |

## 3. Class findings (texts / wrong fields / unknown fields / affected records, d3)

- frame:placing:reserve:2: 219 texts / 14 wrong fields / 0 unknown fields / 14 affected records
- frame:seen:reserve:1: 275 texts / 3 wrong fields / 0 unknown fields / 3 affected records
- role:action:-: 2974 texts / 3 wrong fields / 0 unknown fields
- role:actor:observed_person: 1473 texts / 4 wrong fields / 0 unknown fields
- role:partner:absent: 2734 texts / 10 wrong fields / 0 unknown fields

## 4. Decision consequences (d3)

