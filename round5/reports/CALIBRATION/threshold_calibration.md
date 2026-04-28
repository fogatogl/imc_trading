# Round-5 archetype-threshold calibration

Universe: **50 products** across **10 families**.

Each row in the table below evaluates one hardcoded gate against the empirical distribution of its underlying statistic across all products.
Flag column: `DEGENERATE_HIGH` = ≥95% pass (gate is a no-op), `DEGENERATE_LOW` = ≤5% pass (gate is a blanket exclusion).

```
                gate                       stat direction  value  n_pass  n  frac_pass       p25       p50       p75                                           flag
    pair_corr_strong max_within_family_abs_corr        ge  0.700      20 50       0.40  0.493397  0.645047  0.832660                                               
       pair_corr_min max_within_family_abs_corr        ge  0.500      34 50       0.68  0.493397  0.645047  0.832660                                               
           mr_vr_max                      vr_k5        lt  0.985      19 50       0.38  0.981444  0.987611  1.002130                                               
         mr_acf1_max              acf_ret1_lag1        lt -0.005      27 50       0.54 -0.012116 -0.005453 -0.002461                                               
        mr_hurst_max                      hurst        lt  0.535      20 50       0.40  0.527203  0.536520  0.545124                                               
          mr_adf_max                  adf_p_mid        lt  0.100       6 50       0.12  0.296533  0.450243  0.653831                                               
   mr_vwap_hurst_max                 vwap_hurst        lt  0.500      15 50       0.30  0.484067  0.531320  0.585409                                               
     mr_vwap_adf_max                 vwap_adf_p        lt  0.100       7 50       0.14  0.272246  0.445073  0.648879                                               
           mr_ic_min      ic_neg_zscore_max_abs        ge  0.020      49 50       0.98  0.032538  0.045373  0.056669 DEGENERATE_HIGH (almost no products gated out)
          mom_vr_min                      vr_k5        gt  1.005       9 50       0.18  0.981444  0.987611  1.002130                                               
       mom_hurst_min                      hurst        gt  0.545      13 50       0.26  0.527203  0.536520  0.545124                                               
          mom_ic_min        ic_momentum_max_abs        ge  0.020      34 50       0.68  0.017814  0.024290  0.033996                                               
       rw_vr_dev_max           vr_k5_dev_from_1        lt  0.050      46 50       0.92  0.006117  0.014139  0.019221                                               
    rw_hurst_dev_max        hurst_dev_from_half        lt  0.050      43 50       0.86  0.027203  0.036520  0.045124                                               
     rw_acf1_max_abs          acf_ret1_lag1_abs        lt  0.050      46 50       0.92  0.003480  0.006877  0.012116                                               
           rw_max_ic   ic_short_horizon_max_abs        lt  0.050      27 50       0.54  0.034760  0.048368  0.058846                                               
rw_spread_to_std_min              spread_to_std        ge  1.500       5 50       0.10  0.844371  0.929288  1.267088                                               
    rw_lim10_sat_min         limit10_saturation        ge  0.300      42 50       0.84  0.550717  0.836233  1.000000                                               
          obi_ic_min       ic_obi_max_abs_short        ge  0.040      29 50       0.58  0.031971  0.042794  0.058506                                               
```

## Degenerate gates (likely miscalibrated)
- **mr_ic_min** = 0.02  (ic_neg_zscore_max_abs ge; frac_pass=0.98, p25=0.0325, p50=0.0454, p75=0.0567). _DEGENERATE_HIGH (almost no products gated out)_

Recommended adjustment: move the threshold toward the median (say p25 for `lt`/`le` gates, p75 for `gt`/`ge` gates) and re-run `family_report --family ALL` to see whether the archetype mix changes.
