# c12 Primitive Integer Candidate Coefficients

These are the primitive integer coefficients reconstructed from the primary-prime modular kernel.  They identify the theorem-assisted candidate line; this file is not a full-W annihilation certificate.

The normalization is `a5 gamma34 = 150`, equivalently the rational normalization in the JSON has `a5 gamma34 = 1`.

| Row | Basis element | Primitive coefficient |
|---:|---|---:|
| 0 | `a2^5 f2` | 32 |
| 1 | `a2^4 f4` | -48 |
| 2 | `a2^4 gamma22` | -16 |
| 3 | `a2^3 a3 f3` | -208 |
| 4 | `a2^3 a4 f2` | -192 |
| 5 | `a2^3 gamma24` | 0 |
| 6 | `a2^3 gamma33` | 4 |
| 7 | `a2^2 a3^2 f2` | -312 |
| 8 | `a2^2 a3 f5` | 240 |
| 9 | `a2^2 a3 gamma23` | 92 |
| 10 | `a2^2 a4 f4` | 256 |
| 11 | `a2^2 a4 gamma22` | 96 |
| 12 | `a2^2 a5 f3` | 240 |
| 13 | `a2^2 gamma35` | 40 |
| 14 | `a2^2 gamma44` | 16 |
| 15 | `a2 a3^2 f4` | 288 |
| 16 | `a2 a3^2 gamma22` | 87 |
| 17 | `a2 a3 a4 f3` | 576 |
| 18 | `a2 a3 a5 f2` | 480 |
| 19 | `a2 a3 gamma25` | 60 |
| 20 | `a2 a3 gamma34` | 12 |
| 21 | `a2 a4^2 f2` | 256 |
| 22 | `a2 a4 gamma24` | -64 |
| 23 | `a2 a4 gamma33` | -48 |
| 24 | `a2 a5 f5` | -250 |
| 25 | `a2 a5 gamma23` | -220 |
| 26 | `a2 gamma55` | -35 |
| 27 | `a3^3 f3` | 108 |
| 28 | `a3^2 a4 f2` | 288 |
| 29 | `a3^2 gamma24` | -18 |
| 30 | `a3^2 gamma33` | -18 |
| 31 | `a3 a4 f5` | -450 |
| 32 | `a3 a4 gamma23` | -168 |
| 33 | `a3 a5 f4` | -450 |
| 34 | `a3 a5 gamma22` | -150 |
| 35 | `a3 gamma45` | -90 |
| 36 | `a4^2 f4` | -255 |
| 37 | `a4^2 gamma22` | -64 |
| 38 | `a4 a5 f3` | -450 |
| 39 | `a4 gamma35` | -30 |
| 40 | `a4 gamma44` | 0 |
| 41 | `a5^2 f2` | -125 |
| 42 | `a5 gamma25` | 50 |
| 43 | `a5 gamma34` | 150 |

Omitting the two zero coefficients, the relation candidate is:

```text
32 a2^5 f2
- 48 a2^4 f4
- 16 a2^4 gamma22
- 208 a2^3 a3 f3
- 192 a2^3 a4 f2
+ 4 a2^3 gamma33
- 312 a2^2 a3^2 f2
+ 240 a2^2 a3 f5
+ 92 a2^2 a3 gamma23
+ 256 a2^2 a4 f4
+ 96 a2^2 a4 gamma22
+ 240 a2^2 a5 f3
+ 40 a2^2 gamma35
+ 16 a2^2 gamma44
+ 288 a2 a3^2 f4
+ 87 a2 a3^2 gamma22
+ 576 a2 a3 a4 f3
+ 480 a2 a3 a5 f2
+ 60 a2 a3 gamma25
+ 12 a2 a3 gamma34
+ 256 a2 a4^2 f2
- 64 a2 a4 gamma24
- 48 a2 a4 gamma33
- 250 a2 a5 f5
- 220 a2 a5 gamma23
- 35 a2 gamma55
+ 108 a3^3 f3
+ 288 a3^2 a4 f2
- 18 a3^2 gamma24
- 18 a3^2 gamma33
- 450 a3 a4 f5
- 168 a3 a4 gamma23
- 450 a3 a5 f4
- 150 a3 a5 gamma22
- 90 a3 gamma45
- 255 a4^2 f4
- 64 a4^2 gamma22
- 450 a4 a5 f3
- 30 a4 gamma35
- 125 a5^2 f2
+ 50 a5 gamma25
+ 150 a5 gamma34
= 0
```
