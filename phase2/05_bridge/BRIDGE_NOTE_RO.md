# Reconstrucția unui rezultat Study Contract din arhiva v12

Această notă documentează [recipisa istorică](BRIDGE_RECEIPT.json) și [protocolul înghețat](BRIDGE_PROTOCOL.md) al reconstrucției. Cele opt documente originale au fost recuperate cu identitățile așteptate și sunt distribuite în `study_contract_bridge/sources/` din arhiva de date, alături de inventarul `SOURCE_BINDINGS.json` și adaptorul de reproducere.

Programul a citit direct din arhiva v12 rapoartele păstrate pentru perechea de calificare sintetică `M05E-EQUIV:C24:Q0941`. A verificat amprenta arhivei și amprentele celor șapte fișiere din manifest, apoi a reconstruit populația P din contractul de eligibilitate și din stările păstrate în CSV. Din 200 de poziții inițiale, 156 sunt eligibile și 44 sunt excluse. Cele 156 de poziții coincid, în ordine, cu lista din `study_contract_validation.json` și cu listele de reținere din `pair_binding.json` și `RESULT.json`. Amprenta listei reconstruite și vectorul ordonat al amprentelor identificatorilor au coincis cu valorile păstrate.

| Probă | Observație |
| --- | --- |
| Înregistrarea originală | Nicio abatere. |
| O poziție eligibilă înlocuită cu una exclusă | Reconstrucția a respins lista chiar și după recalcularea amprentei raportului. Lungimea, ordinea și unicitatea listei au rămas valide. |
| Un identificator înlocuit | Vectorul de identitate și cele patru verificări ale amprentelor cadrului au semnalat modificarea. Selecția pe baza stărilor a rămas identică. |
| Lungimea raportată mărită de la 156 la 157 | Verificarea numărului de poziții a semnalat abaterea. Lista și amprenta ei au rămas identice. |

Cititorul are o implementare proprie. Fișierele de intrare provin din aceeași linie de producție arhivată, iar calificarea este sintetică. Verificarea acoperă consistența pozițiilor, a identificatorilor și a lungimilor în fișierele păstrate. Rapoartele originale indică explicit că producătorul și asocierea inițială a datelor cu stările nu au fost verificate. Această probă nu execută P4 sau P5 și nu constituie o replicare pe date independente.

## Reproducere

Ruta portabilă folosește cele opt documente originale livrate. Din rădăcina arhivei de date, rulați cu CPython 3.12 pe Linux:

```sh
python3 -B study_contract_bridge/replay_bridge.py
```

Adaptorul verifică identitățile documentelor și repetă cele patru probe ale protocolului. Recipisa JSON este scrisă la ieșirea standard. `REPLAY_RECEIPT.json` din directorul bridge documentează această reproducere separat de recipisa istorică.

### Ruta originală bazată pe arhivă

Scriptul istoric nemodificat citește arhiva originală exactă, de 53.468.001 octeți, cu SHA-256 `6f758773b489cea9bc17fc36cd30013e24543256631eb2cb9ea53aaf64cd24c5`. Pentru această rută, rulați din rădăcina distribuției software cu CPython 3.12 pe Linux. Înlocuiți calea exemplificată și folosiți un fișier de ieșire nou, în afara distribuției. Programul folosește biblioteca standard Python și citește arhiva fără a o modifica. Codul de ieșire zero al primei comenzi indică trecerea probelor; a doua compară recipisa recalculată cu cea istorică.

```bash
python3 -B phase2/05_bridge/study_contract_bridge.py \
  "/path/to/neuroSEMANTICorr_v12.zip" > ../nsc_bridge_reconstruction.json
cmp phase2/05_bridge/BRIDGE_RECEIPT.json ../nsc_bridge_reconstruction.json
```
