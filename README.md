# RSA-580 / Enigma Subnet 63 — dépôt de reprise

**Dépôt privé : <https://github.com/maxence81/rsa580>**

```bash
git clone https://github.com/maxence81/rsa580.git enigma_rsa
```

Factorisation d'un semi-premier **580 bits** (~175 chiffres, `c175`) par GNFS,
sous la contrainte dure de **14 400 s** (4 h) du validateur Enigma SN63, sur
RTX PRO 6000 96 Go / 24 vCPU / 85 Go RAM, `--network none`, `--read-only`,
`/tmp` en tmpfs 10 Go.

**Statut : non résolu.** Aucune soumission. Tous les leviers de réglage connus
sont fermés et mesurés ; il reste une impasse structurelle documentée (§5).

---

## 1. Verdict en une page

| question | réponse mesurée |
|---|---|
| La limite est-elle vraiment 14 400 s ? | **Oui**, dure, par milestone. Confirmé par l'API publique des challenges (`max_solution_runtime = 14400`), tuée par `solution_container_manager.py:1083`. |
| Le 560 bits a-t-il été résolu dans ce budget ? | **Oui**, par un concurrent (30 soumissions). Notre propre run c169 met 17 339 s → notre chaîne est ~20 % plus lente à réglage comparable. |
| Combien coûte le 580 en 2LP ? | **~18 900 s** au meilleur point mesuré (`lim 100/150`, 24 973 rel/s : 16 740 s de crible + ~2 200 s de LA), soit **~31 % au-dessus** du budget, filtrage non compté. Les autres régimes ne font pas mieux. |
| La 3LP peut-elle sauver la mise ? | **Non.** Mesuré à **46,5 rel/s** contre 4 658 en 2LP : le GPU déborde à chaque q (1,72 M de survivants par q) et retombe sur un repli CPU. 199 M de relations → ~49 jours. |
| Reste-t-il un réglage ? | **Non.** `lim` (10+ runs), polynôme (saturé), `ncurves` (bruit), caps GLAS (OOM ou 0 relation), `SIEVE_A=30` (rien), 3LP (fermé). |
| Que faudrait-il ? | **~1,35× le débit** du cribleur, ou un cribleur GPU capable de 3LP. Les deux sont hors de portée en réglage. |

Le détail chiffré, run par run, est dans `JOURNAL_TENTATIVES.md` (11 sections)
et `rsa580_solver/HANDOFF.md` (16 sections, dont §16 qui corrige §15).

---

## 2. Structure du dépôt

```
enigma_rsa/
├── README.md                  ← ce fichier (point d'entrée)
├── JOURNAL_TENTATIVES.md      ← journal des 8 phases + revue de littérature
├── modal_rsa580.py            ← runner Modal du 580 (POLY_B64, ENV_EXACT)
├── diag_3lp_cofac.py          ← diagnostic 3LP (GLAS_COFAC_DUMP)
├── probe_profile.py           ← sonde zéro-coût pour tester un workspace
├── cof_3lp_stats.txt          ← résultat du diagnostic 3LP (preuve)
├── rsa580_solver/             ← LE solveur 580 (work in progress)
│   ├── Dockerfile             ← image de soumission (glas + CADO + gpu_la)
│   ├── pipeline_c169/
│   │   ├── factor_c175.sh     ← pipeline 580 (dérivé de c160/c169)
│   │   ├── factor_c169.sh     ← pipeline 560, référence qui a produit 420 M rel
│   │   └── stop_cost.py       ← contrôleur d'arrêt (⚠ lire §3.1 avant de le croire)
│   ├── gpu/                   ← patches GLAS (caps, session, xfuse, region…)
│   ├── third_party/cado-nfs-public/   ← arbre CADO Cognition b5ca9c4 + gpu-siever
│   └── tools/cofac_dump_stats.py      ← parseur de dump de cofactorisation
└── rsa560_solver/             ← LE SOLVEUR 560 COMPLET (référence qui marche)
```

`rsa560_solver/` est l'archive de soumission du 560 bits décompressée (elle
s'appelait `964dd74e-…/rsa560_solver`, renommée ici ; aucun chemin du code ne
la référençait). C'est **le point de comparaison le plus utile** : même
Dockerfile, même pipeline, mêmes patches, réglé pour un N plus petit.

---

## 3. Ordre de lecture pour reprendre

1. **`JOURNAL_TENTATIVES.md`** — ce qui a été tenté, dans l'ordre, avec les
   chiffres. Lire §7 (la mesure décisive) et §11 (la 3LP).
2. **`rsa580_solver/HANDOFF.md`** — le relais technique. Lire §1 (le piège du
   prédicteur), §9–10 (modèle de coût), **§15** (verdict), puis **§16** qui
   corrige §15 sur la 3LP.
3. **`rsa580_solver/pipeline_c169/factor_c175.sh`** — le pipeline réel. Le bloc
   de commentaires 120–200 contient l'historique des réglages mesurés.

### 3.1 Deux pièges qui ont coûté des runs entiers

- **`stop_cost.py` clampe** son point de sonde prédit dans
  `[PROBE_AT + PROBE_STEP/2, PROBE_AT + 4×PROBE_STEP]`. Quand le vrai crossover
  est plus loin, la valeur rapportée **est exactement le plafond**
  (`last + 4×PROBE_STEP`). C'est arrivé deux fois. Ne jamais lire ce nombre
  comme une estimation — recalculer sur la pente d'excès mesurée.
- **`modal run --detach` ne survit pas au SIGTERM du client.** Trois apps, dont
  deux runs complets, ont été tuées en fin d'appel shell. **Toujours lancer en
  tâche de fond.**

---

## 4. Lancer quelque chose

### 4.1 Prérequis Modal (deux pièges d'environnement)

```bash
# 1) le bac à sable exporte un proxy que Modal >= 1.6 honore et qui exige
#    python-socks (absent) -> "Could not connect to the Modal server"
#    et "profile misconfigured" sur TOUS les profils. Retirer les variables :
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
    "C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" -m modal ...
```

```python
# 2) l'image builder 2026.10 n'accepte plus Python 3.10 : toute image
#    IMPLICITE (fonction sans image=) doit fixer python_version="3.11".
#    Les images from_dockerfile ne sont pas concernées.
modal.Image.debian_slim(python_version="3.11")
```

Cache d'images : **par workspace**. Un workspace neuf repaie ~40 min de
compilation CADO. Changer une variable `GLAS_*` ne reconstruit que la petite
couche `.env`.

### 4.2 Le diagnostic 3LP (5 min, ~0,3 $)

```bash
cd /c/Users/maxen/enigma_rsa
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
  "C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" \
  -m modal run ./diag_3lp_cofac.py
# puis
python rsa580_solver/tools/cofac_dump_stats.py cof_3lp.bin
```

### 4.3 Un run 580 complet

```bash
cd /c/Users/maxen/enigma_rsa
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
RSA580_CPU_LAS=0 LPB0=32 LPB1=33 MFB0=64 MFB1=66 \
RLIM=70000000 ALIM=100000000 LAMBDA0=2.0352 LAMBDA1=2.0379 \
FIRST_PROBE=200000000 PROBE_STEP=40000000 \
POLY_B64="$(cat /tmp/polyP_b64.txt)" \
"C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" \
    -m modal run --detach ./modal_rsa580.py --difficulty 580 --seed 12345
```

> ⚠ `lim 70/100` **ne tient pas** : c'est la config du run qui a mesuré la
> décroissance de débit (3,55 %/10 M) et réfuté le §13. Le plancher est plutôt
> `lim 100/150`–`120/200`. Voir `JOURNAL_TENTATIVES.md` §7.

---

## 5. Ce qui est fermé, et pourquoi (à ne pas refaire)

| levier | essais | résultat |
|---|---|---|
| `lim` 48/67 → 135/230 | 10+ runs | plancher ~15 500–16 000 s de crible > budget |
| polynôme (MurphyE) | 20 vs 40 batches | saturé : 1,710e-10 vs 1,642e-10 (bruit) |
| `ncurves` 8 vs 17 | run K | −2,5 % (bruit) |
| caps GLAS (margin/surv/hits/fcand) | 4 essais | OOM CUDA, ou 0 relation |
| `SIEVE_A=30` | 1 essai | 0 chunk en 44 min |
| 3LP `mfb 90/92` | 4 essais | **46,5 rel/s**, GPU déborde à chaque q |
| découplage crible/cofactorisation | analyse | ne traite pas le blocage principal (§16.4) |

**La 3LP — le seul régime qui créerait de la marge — est fermée par une limite
structurelle** : avec `mfb=90`, GLAS produit 1,72 M de survivants pour un seul q
(quelques dizaines de milliers en 2LP), déborde même à `surv=2^23`, et retombe
sur un repli CPU à 46 rel/s. Il faudrait une refonte de son buffer de
survivants — GLAS est un binaire Cognition patché, pas un projet refondable ici.

---

## 6. Pistes encore ouvertes (honnêtement)

1. ~~Comprendre l'écart de débit de ~1,35× avec la chaîne 560~~ — **résolu, et ce
   n'était pas un défaut.** Mesure longue du 2026-11-02 (901,6 s, horodatage
   hôte) : le 580 à `lim 100M/150M` fait **24 973 rel/s en moyenne**, 24 117 en
   état stationnaire, avec un pic de fenêtre à 26 946. Le chiffre de 29 614 du
   §13 est **réfuté** (jamais atteint). L'écart avec la chaîne 560 s'explique
   par la **taille de N** : à 560 bits les normes sont plus petites, donc plus
   de relations par q au même `lim`. Voir `HANDOFF.md` §18.4.
2. **Recalculer le budget sur le vrai débit.** À 24 973 rel/s,
   `418 M / 24 973 = 16 740 s` + ~2 200 s de LA = **~18 900 s**, soit **31 %**
   au-dessus de 14 400 s (et davantage avec la décroissance mesurée, ~−6,2 %
   par 10 M). Toute projection antérieure basée sur 29 614 rel/s est à jeter.
3. **Un cribleur GPU qui gère la 3LP.** Aucun n'est disponible ici :
   `bench`/cuda-sieve a été retiré du Dockerfile le 2026-10-25 et sa source
   n'est plus vendored ; `las` (CPU) gère la 3LP mais tourne à 626 rel/s à
   `-t 14` à c160, soit ~50× trop lent.

---

## 7. Comptes Modal

| profil | état (2026-11-02) |
|---|---|
| `lol810-maxou2` | **OK**, utilisé pour les derniers runs |
| `lol810-maxou` | ~42,67 $ dépensés, plafond atteint |
| `maxence81` | 0,00 $ mais plafond à 0 → refusé |
| `maxence7567`, `maxence-dabrowski81` | workspace en pause |

Aucun profil ne peut être débloqué en CLI : le plafond et la pause sont des
actions du dashboard. Un run 580 complet de 4 h coûte **~6–7 $**.

---

## 8. Contrat de sortie du validateur (rappel)

L'image est construite par le validateur depuis le zip de soumission, avec ce
`Dockerfile` à la racine. stdout doit contenir : les logs, le séparateur
`SOLUTION_OUTPUT_SEPARATOR`, puis un zip base64 avec au minimum `result.json`
(`status`, `p`, `q`) et `solve_info.json`. Toute modification du Dockerfile doit
préserver ce contrat.
