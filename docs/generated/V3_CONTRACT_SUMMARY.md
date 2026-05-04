# Dark Factory V3 Contract Summary

protocolReleaseTag: `v3.0-agent-control-r1`

## Source Digests

- `paperclip_darkfactory_v3_0_core_enums.yaml`: `0ac51521c3f04e992f3201bd00d552e1189da5a354f3faf9f92b571462ddefbf` (5808 bytes)
- `paperclip_darkfactory_v3_0_core_objects.schema.json`: `832ee119c3909cd4070f036411109977f2f1ac618432fd2488b6f1b1983afa7d` (23358 bytes)
- `paperclip_darkfactory_v3_0_event_contracts.yaml`: `b8a6ec81c6a1935fdfb2cfd55d0b0e4bb3f6b6d6ba195bc527c9084472a87899` (10208 bytes)
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`: `17e23678a004d2bc8f598088a2af19abfd7d3b13ab92f6fbb12d735f7eab89a1` (12589 bytes)
- `paperclip_darkfactory_v3_0_bundle_manifest.yaml`: `063664fb204c495ce6d66a42979dc6422f682f1f2e961bcd124bc694cea9d905` (19979 bytes)

## Counts

- Enum groups: 31
- Enum literals: 212
- Core object definitions: 45
- Event contracts: 25
- Runtime config entries: 51
- Manifest file entries: 84

## Core Object Definitions

- `ApprovalLevel`
- `ArtifactCertification`
- `ArtifactCertificationState`
- `BlastRadiusClass`
- `Capability`
- `CapsuleHealth`
- `ConsumptionWaiver`
- `ContractDriftReport`
- `ContractDriftStatus`
- `CostLevel`
- `DependencyConsumptionPolicy`
- `ExecutionCapabilityLease`
- `ExecutionSuspensionState`
- `FaultPlaybook`
- `GuardrailDecision`
- `GuardrailDecisionValue`
- `InputDependencyState`
- `IsoDateTime`
- `LineageEdge`
- `ManualGateType`
- `MemoryArtifact`
- `MemoryArtifactState`
- `MemoryArtifactType`
- `ParkRecord`
- `ProfileConformanceStatus`
- `PromptInjectionReceipt`
- `ProviderFailureRecord`
- `ProviderFaultClass`
- `ProviderHealthRecord`
- `ProviderHealthState`
- `RecoveryLane`
- `RehydrationToken`
- `RepairAttempt`
- `RepairOutcome`
- `RiskLevel`
- `RouteDecision`
- `RouteDecisionReason`
- `RouteDecisionReasonCode`
- `RouteDecisionState`
- `ShadowCompareRecord`
- `StringArray`
- `StructuredJournalFact`
- `StructuredJournalFactType`
- `TimingBucketShift`
- `WorkloadClass`

## Event Contracts

- `antibody.pattern.learned` `v1`
- `artifact.certification.changed` `v1`
- `capability.observed` `v1`
- `capsule.preflight.failed` `v1`
- `contract.drift.reported` `v1`
- `fault.playbook.registered` `v1`
- `guardrail.decision.recorded` `v1`
- `journal.fact.extracted` `v1`
- `lineage.invalidation.propagated` `v1`
- `lineage.invalidation.started` `v1`
- `manual_gate.parked` `v1`
- `manual_gate.rehydrated` `v1`
- `memory.artifact.corrected` `v1`
- `memory.artifact.created` `v1`
- `memory.injection.recorded` `v1`
- `provider.failure.recorded` `v1`
- `provider.fallback.activated` `v1`
- `provider.health.observed` `v1`
- `provider.recovered` `v1`
- `repair.attempt.completed` `v1`
- `repair.attempt.started` `v1`
- `route.cutover.performed` `v1`
- `route.decision.recorded` `v1`
- `run.lifecycle.changed` `v3`
- `schema.write_fence.rejected` `v1`

## Batch 4 Surfaces

- `FaultPlaybook`: present
- `StructuredJournalFact`: present
- `ContractDriftReport`: present
- `structuredJournalFactType` enum: 8 values
- `contractDriftStatus` enum: 2 values
