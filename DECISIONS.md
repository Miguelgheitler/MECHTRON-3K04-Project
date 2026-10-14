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
| **ASM-08** | Hardware | Assume all employees have a personal ID card that integrates with a tap system                                                            | Provides an option for multi-factor authentification | 
| **ASM-09** | Security | Assume hospital security policies recommend a 2-minute timeout duration                                                                   | Justifies the somewhat arbitrary choice of time frame | 
| **ASM-10** | Data | Assume the monitoring system has access to shift schedules, notably can check (Y/N) if a specified employee is working                        | Provides a layer of security | 
| **ASM-11** | Hardware | Assume that most employees possess a cell phone capable of a face ID check                                                                | Provides a layer of security | 


## 2. Architectural & Design Decisions

|**Decision ID**|**Topic**|**Choice Made**|**Alternatives Considered**|**Why We Chose This**|
|---|---|---|---|---|
| **DEC-LOG-001** | Event Timestamp Precision | Dual-Precision Time: Store millisecond UTC timestamps in the database; truncate to second-level (`YYYY-MM-DD HH:MM:SS`) on front-end UIs and reports. | 1. **Second-Level Only:** Inadequate for handling high-volume concurrent network packet sync bursts.<br>2. **Millisecond Everywhere:** Adds visual noise and formatting cognitive load for clinical auditors. | **System Concurrency:** Millisecond backend tracking is mandatory to prevent data deadlocks, sort asynchronous network bursts from multiple cabinets, and resolve race conditions.<br><br>**Human Usability:** Second-level front-end display aligns with standard hospital security footage and EHR entry formats for clean drug diversion auditing.<br><br>**Zero Storage Penalty:** Modern database engines allocate fixed binary bytes (7-8 bytes) regardless of truncation, meaning millisecond tracking provides maximum integrity at zero data storage cost. |

## 3. Ethical & Safety Considerations

- **Patient Safety:** Prevent incorrect dispensing, unauthorized access, or hidden device failures because both the ADC and Monitoring System are safety-critical systems where malfunctions can cause direct harm.
    
- **Data Privacy & Traceability:** Ensure all operational activities, inventory adjustments, and system alarms are permanently recorded and restricted to authorized personnel (nurses, pharmacists, administrators) to maintain compliance and auditability.
    
- **Controlled Access:** Enforce strict authentication checks so that only permitted users can perform protected actions or access specific medications.

**Accessibility:** Multi-Channel Notification Flexibility (US-ALRM-02 / FR-ALRM-03): By giving staff the flexibility to receive alerts through multiple avenues (SMS, email, or designated app notifications), the system accommodates different user preferences, device types, and individual communication needs.

Cognitive Load Management(FR-ALRM-02): Directing alarms explicitly to the appropriate individuals based on roles prevents broadcast fatigue. In high-stress clinical environments, filtering out irrelevant alarms ensures that healthcare workers can focus on actionable alerts without cognitive overload.

Interface & Device Adaptability (FR-ALRM-03 and US-ALRM-02, Scenario 3 ): Allowing staff to manage and toggle their notification preferences through authorized devices ensures that the notification mechanism aligns with what each individual can effectively access and monitor while on shift.
  
