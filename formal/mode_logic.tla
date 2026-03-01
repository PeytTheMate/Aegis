------------------------------ MODULE mode_logic ------------------------------
EXTENDS Naturals, Sequences

CONSTANT AbortDelay

Modes == {"NOMINAL", "ABORT_PENDING", "ABORT"}

VARIABLES mode, abortRequested, pendingSteps, hazardDetected, imuHealthy

Init ==
  /\ mode = "NOMINAL"
  /\ abortRequested = FALSE
  /\ pendingSteps = 0
  /\ hazardDetected \in BOOLEAN
  /\ imuHealthy \in BOOLEAN

Next ==
  \/ /\ mode = "ABORT"
     /\ mode' = "ABORT"
     /\ abortRequested' = abortRequested
     /\ pendingSteps' = pendingSteps
     /\ hazardDetected' \in BOOLEAN
     /\ imuHealthy' \in BOOLEAN
  \/ /\ mode # "ABORT"
     /\ hazardDetected' \in BOOLEAN
     /\ imuHealthy' \in BOOLEAN
     /\ abortRequested' = abortRequested \/ (hazardDetected' /\ imuHealthy')
     /\ IF mode = "NOMINAL" /\ abortRequested'
           THEN /\ mode' = "ABORT_PENDING"
                /\ pendingSteps' = 0
           ELSE IF mode = "ABORT_PENDING"
             THEN /\ pendingSteps' = pendingSteps + 1
                  /\ mode' = IF pendingSteps' >= AbortDelay THEN "ABORT" ELSE "ABORT_PENDING"
             ELSE /\ mode' = "NOMINAL"
                  /\ pendingSteps' = 0

ModeInDomain == mode \in Modes
AbortAbsorbing == mode = "ABORT" => mode' = "ABORT"

Spec == Init /\ [][Next]_<<mode, abortRequested, pendingSteps, hazardDetected, imuHealthy>>

=============================================================================
