# Project Decisions and Assumptions Log

## 1. Context & Scope Assumptions

| **ID**     | **Category** | **Assumption / Gap Filled**                                                                                                           | **Rationale & Impact**                                                                                                               |
| ---------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **ASM-01** | Network      | Assume the hospital network infrastructure is available, but the ADC can operate locally and handle communication losses temporarily. | Shapes requirements for local event logging, reliability, and offline resilience during network drops.                               |
| **ASM-02** | Hardware     | Assume physical cabinet hardware, electronic locks, drawers, sensors, and actuators already exist and provide software APIs.          | Keeps mechanical design, drawer mechanisms, and internal hardware details strictly out of scope.                                     |
| **ASM-03** | Users & Auth | Assume a means of capturing user credentials at the cabinet is available and users have valid accounts.                               | Enables the implementation of strict access control enforcement and role-based permissions for nurses, pharmacists, and technicians. |

## 2. Architectural & Design Decisions

|**Decision ID**|**Topic**|**Choice Made**|**Alternatives Considered**|**Why We Chose This**|
|---|---|---|---|---|
|**DEC-01**|Integration Boundary|Define an explicit network boundary between the local ADC software and the centralized Monitoring System for telemetry exchange.|Direct database sharing or monolithic deployment.|Aligns with the project requirement for two independently designed software systems to communicate via defined interfaces.|
|**DEC-02**|Operational Modes|Implement explicit state-machine operational modes (normal operation, maintenance, and fault conditions).|Unstructured runtime states.|Manages safety-critical dispensing behaviors and handles abnormal hardware/software conditions safely.|

## 3. Ethical & Safety Considerations

- **Patient Safety:** Prevent incorrect dispensing, unauthorized access, or hidden device failures because both the ADC and Monitoring System are safety-critical systems where malfunctions can cause direct harm.
    
- **Data Privacy & Traceability:** Ensure all operational activities, inventory adjustments, and system alarms are permanently recorded and restricted to authorized personnel (nurses, pharmacists, administrators) to maintain compliance and auditability.
    
- **Controlled Access:** Enforce strict authentication checks so that only permitted users can perform protected actions or access specific medications.
  
