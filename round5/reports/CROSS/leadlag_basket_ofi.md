# Basket-vs-leg lead-lag: mid vs OFI (LOO baskets)

Predictor: mid = basket Δmid_{t-L}. ofi = basket signed-volume_{t-L}. Target always Δmid_t. Basket excludes target leg (LOO). Lags scanned: [1, 2, 3, 4, 5]. Sign-stability across days [2, 3, 4].

## Top 15 sign-stable (mid predictor)

| family | leg | lag | mean_corr | min | max |
|---|---|---:|---:|---:|---:|
| SNACKPACK | PISTACHIO | 1 | -0.0836 | -0.0966 | -0.0752 |
| SNACKPACK | STRAWBERRY | 1 | -0.0490 | -0.0610 | -0.0339 |
| SNACKPACK | VANILLA | 1 | -0.0287 | -0.0326 | -0.0248 |
| SNACKPACK | CHOCOLATE | 1 | -0.0252 | -0.0295 | -0.0175 |
| TRANSLATOR | SPACE_GRAY | 1 | -0.0185 | -0.0319 | -0.0036 |
| PEBBLES | S | 3 | +0.0179 | +0.0010 | +0.0295 |
| OXYGEN_SHAKE | EVENING_BREATH | 5 | -0.0175 | -0.0206 | -0.0135 |
| TRANSLATOR | ASTRO_BLACK | 4 | +0.0157 | +0.0084 | +0.0273 |
| GALAXY_SOUNDS | DARK_MATTER | 1 | -0.0156 | -0.0316 | -0.0006 |
| OXYGEN_SHAKE | EVENING_BREATH | 1 | -0.0151 | -0.0231 | -0.0056 |
| SNACKPACK | RASPBERRY | 1 | -0.0148 | -0.0201 | -0.0108 |
| PEBBLES | S | 1 | -0.0142 | -0.0223 | -0.0031 |
| SNACKPACK | RASPBERRY | 2 | -0.0133 | -0.0212 | -0.0080 |
| MICROCHIP | CIRCLE | 3 | +0.0128 | +0.0047 | +0.0186 |
| PEBBLES | L | 1 | -0.0128 | -0.0192 | -0.0073 |

## Top 15 sign-stable (ofi predictor)

| family | leg | lag | mean_corr | min | max |
|---|---|---:|---:|---:|---:|
| TRANSLATOR | VOID_BLUE | 2 | +0.0152 | +0.0055 | +0.0256 |
| OXYGEN_SHAKE | MINT | 2 | +0.0150 | +0.0120 | +0.0196 |
| PANEL | 4X4 | 4 | -0.0141 | -0.0232 | -0.0028 |
| UV_VISOR | MAGENTA | 5 | +0.0132 | +0.0086 | +0.0210 |
| TRANSLATOR | ECLIPSE_CHARCOAL | 2 | +0.0131 | +0.0071 | +0.0195 |
| UV_VISOR | YELLOW | 1 | +0.0130 | +0.0116 | +0.0142 |
| ROBOT | DISHES | 4 | +0.0121 | +0.0023 | +0.0176 |
| OXYGEN_SHAKE | CHOCOLATE | 4 | -0.0120 | -0.0197 | -0.0081 |
| ROBOT | IRONING | 4 | +0.0117 | +0.0089 | +0.0141 |
| MICROCHIP | SQUARE | 5 | -0.0113 | -0.0156 | -0.0041 |
| OXYGEN_SHAKE | GARLIC | 4 | -0.0113 | -0.0209 | -0.0038 |
| SNACKPACK | STRAWBERRY | 3 | -0.0112 | -0.0169 | -0.0053 |
| UV_VISOR | RED | 2 | +0.0112 | +0.0003 | +0.0252 |
| ROBOT | LAUNDRY | 5 | -0.0112 | -0.0297 | -0.0018 |
| PANEL | 4X4 | 2 | -0.0105 | -0.0230 | -0.0014 |

## Side-by-side best-lag per leg (sorted by |OFI corr|)

| family | leg | mid_corr | mid_lag | mid_stable | ofi_corr | ofi_lag | ofi_stable | ofi/mid ratio |
|---|---|---:|---:|:---:|---:|---:|:---:|---:|
| TRANSLATOR | VOID_BLUE | -0.0064 | 1 | - | +0.0152 | 2 | Y | 2.36x |
| OXYGEN_SHAKE | MINT | -0.0069 | 1 | - | +0.0150 | 2 | Y | 2.17x |
| PANEL | 4X4 | +0.0053 | 3 | Y | -0.0141 | 4 | Y | 2.67x |
| UV_VISOR | MAGENTA | +0.0095 | 4 | Y | +0.0132 | 5 | Y | 1.39x |
| TRANSLATOR | ECLIPSE_CHARCOAL | +0.0089 | 3 | Y | +0.0131 | 2 | Y | 1.48x |
| UV_VISOR | YELLOW | -0.0038 | 1 | - | +0.0130 | 1 | Y | 3.41x |
| PANEL | 1X2 | +0.0067 | 2 | - | +0.0127 | 4 | - | 1.90x |
| ROBOT | DISHES | -0.0078 | 3 | - | +0.0121 | 4 | Y | 1.55x |
| MICROCHIP | RECTANGLE | +0.0084 | 2 | - | +0.0120 | 4 | - | 1.44x |
| OXYGEN_SHAKE | CHOCOLATE | -0.0074 | 3 | - | -0.0120 | 4 | Y | 1.63x |
| ROBOT | IRONING | +0.0080 | 5 | Y | +0.0117 | 4 | Y | 1.46x |
| PANEL | 2X2 | -0.0072 | 1 | Y | -0.0114 | 2 | - | 1.58x |
| MICROCHIP | SQUARE | +0.0045 | 1 | Y | -0.0113 | 5 | Y | 2.50x |
| OXYGEN_SHAKE | GARLIC | -0.0080 | 1 | Y | -0.0113 | 4 | Y | 1.41x |
| SNACKPACK | STRAWBERRY | -0.0490 | 1 | Y | -0.0112 | 3 | Y | 0.23x |
| UV_VISOR | RED | -0.0128 | 1 | Y | +0.0112 | 2 | Y | 0.88x |
| ROBOT | LAUNDRY | -0.0085 | 2 | Y | -0.0112 | 5 | Y | 1.31x |
| SNACKPACK | CHOCOLATE | -0.0252 | 1 | Y | +0.0099 | 1 | Y | 0.39x |
| PANEL | 1X4 | -0.0114 | 4 | Y | -0.0098 | 2 | Y | 0.86x |
| PEBBLES | M | -0.0099 | 5 | Y | +0.0097 | 1 | Y | 0.98x |
| GALAXY_SOUNDS | PLANETARY_RINGS | +0.0099 | 5 | Y | -0.0097 | 2 | - | 0.97x |
| MICROCHIP | CIRCLE | +0.0128 | 3 | Y | -0.0097 | 3 | Y | 0.75x |
| SNACKPACK | PISTACHIO | -0.0836 | 1 | Y | -0.0094 | 3 | Y | 0.11x |
| SLEEP_POD | COTTON | +0.0122 | 5 | - | -0.0093 | 3 | Y | 0.76x |
| TRANSLATOR | GRAPHITE_MIST | -0.0071 | 5 | - | +0.0089 | 2 | Y | 1.26x |
| OXYGEN_SHAKE | EVENING_BREATH | -0.0175 | 5 | Y | -0.0088 | 3 | - | 0.50x |
| ROBOT | VACUUMING | +0.0107 | 2 | - | +0.0088 | 5 | Y | 0.82x |
| MICROCHIP | OVAL | +0.0053 | 1 | - | -0.0087 | 1 | - | 1.66x |
| SLEEP_POD | NYLON | -0.0041 | 3 | - | -0.0086 | 5 | - | 2.10x |
| PEBBLES | XL | -0.0110 | 5 | - | -0.0086 | 5 | - | 0.78x |
| GALAXY_SOUNDS | SOLAR_FLAMES | +0.0077 | 4 | - | +0.0083 | 4 | Y | 1.07x |
| UV_VISOR | ORANGE | -0.0064 | 4 | Y | +0.0082 | 2 | Y | 1.28x |
| PEBBLES | L | -0.0128 | 1 | Y | +0.0081 | 1 | Y | 0.63x |
| SLEEP_POD | POLYESTER | +0.0060 | 4 | Y | -0.0077 | 3 | Y | 1.29x |
| GALAXY_SOUNDS | SOLAR_WINDS | -0.0099 | 4 | Y | -0.0076 | 5 | - | 0.77x |
| SNACKPACK | RASPBERRY | -0.0148 | 1 | Y | +0.0076 | 3 | - | 0.51x |
| ROBOT | MOPPING | +0.0078 | 5 | - | +0.0074 | 4 | Y | 0.96x |
| OXYGEN_SHAKE | MORNING_BREATH | +0.0088 | 1 | Y | +0.0074 | 3 | - | 0.84x |
| SNACKPACK | VANILLA | -0.0287 | 1 | Y | -0.0074 | 1 | Y | 0.26x |
| PEBBLES | XS | +0.0099 | 1 | Y | +0.0067 | 5 | Y | 0.67x |
| TRANSLATOR | SPACE_GRAY | -0.0185 | 1 | Y | -0.0060 | 3 | - | 0.32x |
| MICROCHIP | TRIANGLE | -0.0079 | 3 | Y | -0.0059 | 1 | Y | 0.75x |
| SLEEP_POD | SUEDE | +0.0089 | 1 | Y | +0.0056 | 4 | - | 0.63x |
| GALAXY_SOUNDS | BLACK_HOLES | -0.0065 | 1 | - | +0.0047 | 4 | Y | 0.73x |
| PEBBLES | S | +0.0179 | 3 | Y | -0.0044 | 1 | Y | 0.25x |
| PANEL | 2X4 | +0.0111 | 5 | Y | +0.0043 | 2 | Y | 0.39x |
| SLEEP_POD | LAMB_WOOL | -0.0092 | 4 | Y | -0.0042 | 3 | - | 0.46x |
| UV_VISOR | AMBER | -0.0122 | 5 | Y | -0.0039 | 5 | Y | 0.32x |
| TRANSLATOR | ASTRO_BLACK | +0.0157 | 4 | Y | -0.0039 | 4 | - | 0.25x |
| GALAXY_SOUNDS | DARK_MATTER | -0.0156 | 1 | Y | +0.0037 | 4 | - | 0.24x |
