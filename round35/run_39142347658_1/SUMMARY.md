# Round 3.5 timing run

## qwen2.5-0.5b

- texts timed: 168; seconds per text: mean 17.50, median 16.82, max 23.89; model loading 8 s
- cache check (10 texts, all slots): max |cached - uncached| 1.56e-04, same choices True -> OK
- dev: 750 distinct texts, about 3.6 h of encoding -> at least 1 chunk(s) of < 5.5 h (plus loading)
- cal: 748 distinct texts, about 3.6 h of encoding -> at least 1 chunk(s) of < 5.5 h (plus loading)
- ho: 2974 distinct texts, about 14.5 h of encoding -> at least 3 chunk(s) of < 5.5 h (plus loading)

## qwen3-0.6b

- texts timed: 168; seconds per text: mean 29.08, median 27.79, max 39.62; model loading 12 s
- cache check (10 texts, all slots): max |cached - uncached| 2.04e-04, same choices True -> OK
- dev: 750 distinct texts, about 6.1 h of encoding -> at least 2 chunk(s) of < 5.5 h (plus loading)
- cal: 748 distinct texts, about 6.0 h of encoding -> at least 2 chunk(s) of < 5.5 h (plus loading)
- ho: 2974 distinct texts, about 24.0 h of encoding -> at least 5 chunk(s) of < 5.5 h (plus loading)

