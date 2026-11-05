# Licensing and attribution

Package-authored scripts, registries, and documentation use the repository MIT
license (`LICENSE` at the repository root). The Diagnosis tool snapshot follows its
bundled license in `tool/LICENSE`.

Input requirements and traces originate from the cited Diagnosis and
running-example repositories; see `inputs/provenance/inputs.csv`. They are fixed
primary research inputs and retain their upstream terms. Weka 3.8.6 is GPL-3.0,
Z3 is MIT, RTAMT is BSD-3-Clause, Graphviz is EPL-1.0, NumPy/SciPy/Matplotlib use
their respective BSD/PSF-compatible licenses. Bounce 0.18 is bundled because
Weka requires it; its embedded Maven POM declares “BSD License” but the JAR does
not include a license text. Bounce redistribution follows its upstream terms;
this inventory does not replace or override them.

TD-SB-TemPsy is not bundled. The pinned public upstream declares Apache-2.0;
`experiments/baseline_td_sb_tempsy/fetch_and_patch.sh` retrieves the exact
upstream and reproducibility-patch commits while retaining their license and
attribution files.
