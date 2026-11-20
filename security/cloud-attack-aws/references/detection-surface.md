# CloudTrail / GuardDuty detection-surface awareness (`T1562.008`, awareness not evasion)

Feeds Step 4 of `../SKILL.md`. Per **D5**, this skill teaches what an authorized action **emits** — so a
tester knows their footprint and a defender knows what to tune — and **never** how to evade detection
against a real target.

## CloudTrail — management vs data events

**Management events** (control-plane: IAM changes, `RunInstances`, `ModifyDBSnapshotAttribute`,
`PutBucketPolicy`, `AssumeRole`, `CreateAccessKey`) are **on by default** where a trail is configured,
recorded with `eventName`, `userIdentity` (`IAMUser` vs `AssumedRole` vs `Root`), `sourceIPAddress`, and
`userAgent` (`aws-cli`, `Boto3`, `pacu` — the attribution fields). Nearly every privesc action is a
management event. **Data events** (S3 `GetObject`/`PutObject`, Lambda `Invoke`, DynamoDB item ops) are
**off by default** — so S3 object reads are often *not* logged; check `cloudtrail:GetEventSelectors` to
know whether they are, and report "object reads unlogged" as a **defender-coverage gap**, never exploit it
as a stealth feature.

## GuardDuty — findings to name in the report

GuardDuty fires findings off CloudTrail, VPC Flow Logs, and DNS logs. Name the finding each technique
tends to trip so the report states what *should* have fired:
`UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS` (instance creds used off the
instance — the EC2 IMDS-theft signature), `.InsideAWS` (used from another account),
`PrivilegeEscalation:IAMUser/AnomalousBehavior` and `Persistence:IAMUser/AnomalousBehavior` (anomalous IAM
mutation), `CredentialAccess:IAMUser/AnomalousBehavior`, `Policy:S3/BucketPublicAccessGranted`, and the
tamper indicators `Stealth:IAMUser/CloudTrailLoggingDisabled` / `PasswordPolicyChange` (named so a tester
knows these *would* fire — the skill never teaches disabling logging).

## Pairing rule

Every attack technique above is reported with its CloudTrail `eventName` and the GuardDuty finding it
tends to trigger, so the learner reasons about footprint. Confirming an authorized action surfaced as a
GuardDuty finding is purple-team value — it closes the detection loop the lab exists to teach.
