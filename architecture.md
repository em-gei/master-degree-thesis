=============================================================================================================
                                      LIVELLO 1: ACQUISIZIONE DATI (HARDWARE)
=============================================================================================================
      (Alcool)         (Giroscopio)          (Camera)             (Gas)  (Temp/Umid)  (Luce)  (Audio)
         |               |      |               |                   |         |         |        |
         |      +--------+      +-------+       |                   |         |         |        |
         v      v                       v       v                   v         v         v        v
=============================================================================================================
                                      LIVELLO 2: ELABORAZIONE SOFTWARE (UNITS)
=============================================================================================================
+-------------------------+      +---------------------------+      +---------------------------------------+
|      CRITICAL UNIT      |      |  KINEMATIC & BEHAVIORAL   |      |      CONTEXT & ENVIRONMENT UNIT       |
| (Regole Deterministiche)|      |           UNIT            |      |       (Regole Deterministiche)        |
|                         |      |                           |      |                                       |
| - Dati Istantanei Raw   |      | [ Creazione Windows 3s ]  |      | - Dati Istantanei / Medie Lente       |
| - Check Soglia Alcool   |      | - EAR_mean, EAR_min       |      | - Check Gas (Rischio Asfissia/CO2)    |
| - Check Urto (es. > 5G) |      | - Pitch/Yaw/Gyro_std      |      | - Check Temp/Umid (Stress Termico)    |
|                         |      |             |             |      | - Check Luce (Salute Telecamera)      |
|                         |      |             v             |      | - Check Audio (Frenate/Urto Esterno)  |
|                         |      |     [ Modello ML ]        |      |                                       |
|                         |      |      ( LightGBM )         |      |                                       |
+-------------------------+      +---------------------------+      +---------------------------------------+
             |                                 |                                        |
             |  [Allarmi:                      |  [Predizione:                          |  [Warning:
             |   EBBREZZA,                     |   VIGILE, DISTRAZIONE,                 |   QUALITÀ ARIA,
             |   CRASH]                        |   SONNOLENZA, MALORE]                  |   BUIO, CALORE]
             |                                 |                                        |
=============================================================================================================
                                      LIVELLO 3: DECISIONE (ARBITRATOR)
=============================================================================================================
             |                                 |                                        |
             +------------------------+        |        +-------------------------------+
                                      v        v        v
                                 +---------------------------+
                                 |    PRIORITY ARBITRATOR    |
                                 |  (Motore di Risoluzione)  |
                                 |                           |
                                 | Priorita 1: Critical Unit |
                                 | Priorita 2: Predizione ML |
                                 | Modificatori: Environment |
                                 +---------------------------+
                                               |
                                               v
=============================================================================================================
                                      LIVELLO 4: ESECUZIONE (OUTPUT)
=============================================================================================================
                                       [ OUTPUT FINALE ]
        (Attivazione Matrice LED (improvements Display, Blocco Motore, Chiamata di Emergenza e-Call))