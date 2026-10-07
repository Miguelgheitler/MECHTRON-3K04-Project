# Project Decisions and Assumptions Log

## 1. Context & Scope Assumptions

| **ID**     | **Category** | **Assumption / Gap Filled**                                                                                                           | **Rationale & Impact**                                                                                                               |
| ---------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **ASM-01** | Network      | Assume the hospital network infrastructure is available, but the ADC can operate locally and handle communication losses temporarily. | Shapes requirements for local event logging, reliability, and offline resilience during network drops.                               |
| **ASM-02** | Hardware     | Assume physical cabinet hardware, electronic locks, drawers, sensors, and actuators already exist and provide software APIs.          | Keeps mechanical design, drawer mechanisms, and internal hardware details strictly out of scope.                                     |
| **ASM-03** | Users & Auth | Assume a means of capturing user credentials at the cabinet is available and users have valid accounts.                               | Enables the implementation of strict access control enforcement and role-based permissions for nurses, pharmacists, and technicians. |
| **ASM-04** | Fault Handling | Assume at worst, issues are escalated to and guaranteed to be resolved by the project manager                                       | Sets the extent to which issues/alerts are expected to be escalated by the system. |
| **ASM-05** | Data | Assume all medication data (dosage, storage requirements, administration instructions, etc) is available.                                     | Allows use of medication to be automatically monitored |
| **ASM-06** | Staffing | Assume nurses and pharmacists are assigned specific ADC units for which to review alerts                                                  | Shapes the hierarchy for alarm management; allows better organization than all alarms being sent to all hospital employees |
| **ASM-07** | Network | Assume the monitoring system is capable of detecting when an alarm fails to be received by recipient device                                | Keeps software regarding detection of connection failure strictly out of scope. | 

## 2. Architectural & Design Decisions

|**Decision ID**|**Topic**|**Choice Made**|**Alternatives Considered**|**Why We Chose This**|
|---|---|---|---|---|

## 3. Ethical & Safety Considerations

- **Patient Safety:** Prevent incorrect dispensing, unauthorized access, or hidden device failures because both the ADC and Monitoring System are safety-critical systems where malfunctions can cause direct harm.
    
- **Data Privacy & Traceability:** Ensure all operational activities, inventory adjustments, and system alarms are permanently recorded and restricted to authorized personnel (nurses, pharmacists, administrators) to maintain compliance and auditability.
    
- **Controlled Access:** Enforce strict authentication checks so that only permitted users can perform protected actions or access specific medications.

**Accessibility:** Multi-Channel Notification Flexibility (US-ALRM-02 / FR-ALRM-03): By giving staff the flexibility to receive alerts through multiple avenues (SMS, email, or designated app notifications), the system accommodates different user preferences, device types, and individual communication needs.

Cognitive Load & Alert Fatigue Management (FR-ALRM-02): Directing alarms explicitly to the appropriate individuals based on roles prevents broadcast fatigue. In high-stress clinical environments, filtering out irrelevant alarms ensures that healthcare workers can focus on actionable alerts without cognitive overload.

Interface & Device Adaptability (US-ALRM-02, Scenario 3): Allowing staff to manage and toggle their notification preferences through authorized devices ensures that the notification mechanism aligns with what each individual can effectively access and monitor while on shift.
  
