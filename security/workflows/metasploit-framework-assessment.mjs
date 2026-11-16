export const meta = {
  name: 'metasploit-framework-assessment',
  description: 'Free/open-source Metasploit Framework lane. Read a repo statically, derive its deploy profile, and produce a Framework setup + test plan (msfconsole modules, msfvenom payloads, the Framework MCP server) and a pre-filled engagement scope-file skeleton. Plans only — never touches a live target or runs an exploit; live execution stays with the gated /penetration-testing:pentest agent. The paid Metasploit Pro lane is a separate workflow (see docs/plans).',
  whenToUse: 'Given a repository, decide the open-source Metasploit Framework setup and the exact modules/tests to run against its deployment, stopping at the authorization gate.',
  phases: [
    { title: 'Profile', detail: 'three parallel readers: infra/ports, dependency CVE leads, app/auth fingerprint' },
    { title: 'Plan', detail: 'synthesize the profile into a setup + test plan and a scope-file skeleton' },
    { title: 'Review', detail: 'adversarial completeness critic: missed surfaces, out-of-reach, overreach' },
  ],
}

const SONNET = { model: 'sonnet', effort: 'medium' }
const repo = (args && args.repo) || '.'
const targetHint = (args && args.targetHint) || '(none given — the human names the deployed lab target in the scope file)'

const SAFETY = [
  'STATIC PLANNING ONLY. Read files with Read/Grep/Glob/Bash (ls, cat, find) over the repo path.',
  'Do NOT run any scanner, network tool, nmap, curl against a host, msfconsole, or exploit.',
  'Do NOT touch any live host. You are reading source to plan, not attacking anything.',
].join(' ')

phase('Profile')

const INFRA_SCHEMA = {
  type: 'object',
  properties: {
    services: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          port: { type: 'integer' },
          proto: { type: 'string' },
          name: { type: 'string' },
          version: { type: 'string' },
          source: { type: 'string', description: 'file + line the port/service came from' },
        },
        required: ['name', 'source'],
      },
    },
    networkPosture: { type: 'string', description: 'egress/ingress shape, reverse vs bind implication, exposed vs internal' },
    deployment: { type: 'string', description: 'how and where it deploys (compose/k8s/cloud), any target hint for recon' },
    notes: { type: 'string' },
  },
  required: ['services'],
}

const DEPS_SCHEMA = {
  type: 'object',
  properties: {
    stack: {
      type: 'array',
      items: {
        type: 'object',
        properties: { name: { type: 'string' }, version: { type: 'string' } },
        required: ['name'],
      },
    },
    cveLeads: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          component: { type: 'string' },
          version: { type: 'string' },
          cve: { type: 'string', description: 'CVE id if known, else empty' },
          severity: { type: 'string' },
          moduleHint: { type: 'string', description: 'likely msf search term or module path, e.g. "search cve:2021-44228" / exploit/multi/http/log4shell_header_injection' },
          source: { type: 'string', description: 'manifest file + the pinned version line' },
        },
        required: ['component', 'moduleHint', 'source'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['cveLeads'],
}

const APP_SCHEMA = {
  type: 'object',
  properties: {
    framework: { type: 'string' },
    authModel: { type: 'string', description: 'form/JWT/OAuth/LDAP-AD/SSH/basic + where creds live' },
    managementEndpoints: { type: 'array', items: { type: 'string' }, description: 'actuator/admin/debug/metrics surfaces with their path' },
    defaultCredRisks: { type: 'array', items: { type: 'string' } },
    webSurfaces: { type: 'array', items: { type: 'string' }, description: 'notable routes/upload/deserialization sinks' },
    notes: { type: 'string' },
  },
  required: ['framework', 'authModel'],
}

const [infra, deps, app] = await parallel([
  () => agent(
    `${SAFETY}\n\nAssess the repository at "${repo}" for its INFRASTRUCTURE / network exposure only.\n` +
    `Read Dockerfiles, docker-compose*.yml, k8s manifests, Helm charts, Terraform/CloudFormation/Pulumi/Ansible, nginx/apache configs, and any process/port config.\n` +
    `Return every exposed service and port (EXPOSE, ports:, Service/Ingress, listen directives), the base images (OS/runtime), the network posture (is egress likely filtered? is the app internet-facing or internal? which implies reverse vs bind payloads), and how/where it deploys. Cite file+line in "source".`,
    { ...SONNET, label: 'profile:infra', phase: 'Profile', schema: INFRA_SCHEMA },
  ),
  () => agent(
    `${SAFETY}\n\nAssess the repository at "${repo}" for DEPENDENCY / known-CVE leads only.\n` +
    `Read dependency manifests and lockfiles (pom.xml, build.gradle, package.json + lock, requirements.txt, uv.lock, *.csproj, Gemfile.lock, go.mod, Cargo.toml) and the base-image tags.\n` +
    `List pinned components whose version has a known exploitable CVE reachable by a Metasploit module (Log4j/Log4Shell, Struts2, Spring, Rails, Confluence, Jenkins, Exchange, etc.). For each, give the component+version, the CVE if known, and a "moduleHint" (an msf "search cve:..." term or a concrete module path). Cite the manifest file + the exact pinned version line. This is the highest-signal input — be precise about versions, do not guess exploitability beyond the pinned version.`,
    { ...SONNET, label: 'profile:deps', phase: 'Profile', schema: DEPS_SCHEMA },
  ),
  () => agent(
    `${SAFETY}\n\nAssess the repository at "${repo}" for APPLICATION framework / auth / surface only.\n` +
    `Identify the web framework and version, the auth model (form/JWT/OAuth/LDAP-AD/SSH/basic and where credentials live), management/debug endpoints (Spring actuator, admin panels, metrics, debug toggles), default-credential patterns, and notable web surfaces (file upload, deserialization sinks, SSRF-prone routes). Read app config (application.yml, web.xml, appsettings.json, .env.example) and route/controller code.`,
    { ...SONNET, label: 'profile:app', phase: 'Profile', schema: APP_SCHEMA },
  ),
])

const profile = { infra, deps, app }
log(`Profile done: ${infra?.services?.length ?? 0} services, ${deps?.cveLeads?.length ?? 0} CVE leads, framework ${app?.framework ?? 'unknown'}`)

phase('Plan')

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    workspace: { type: 'string', description: 'engagement-<NNN> style msf workspace name' },
    setup: { type: 'string', description: 'toolchain setup: Docker image pinned by digest, msfdb workspace, MCP server read-only; note if a lab deployment must be stood up first' },
    tests: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          surface: { type: 'string', description: 'the service/CVE/surface this tests' },
          module: { type: 'string', description: 'concrete msf module path or search term' },
          action: { type: 'string', description: 'check-then-run, scan, cred-test (lockout-aware), etc.' },
          operatorCommand: { type: 'string', description: 'the exact msfconsole lines (use/set/check/run) or msfvenom line the authorized human operator runs for this test, LHOST/LPORT filled from the profile — ready to paste, since the live act is operator-run' },
          payloadShape: { type: 'string', description: 'reverse/bind + staged/stageless + LPORT rationale, or n/a' },
          provenOutcome: { type: 'string', description: 'the single expected result that counts as proven (no OR)' },
          attackId: { type: 'string', description: 'MITRE ATT&CK technique id' },
          availabilityRisk: { type: 'boolean', description: 'true if the module may crash the service (memory-corruption / manual rank) — needs per-act sign-off, never production' },
        },
        required: ['surface', 'module', 'action', 'provenOutcome'],
      },
    },
    scopeFileSkeleton: { type: 'string', description: 'a docs/security/engagement-<NNN>.md markdown skeleton pre-filled with the derived in-scope surface, hard exclusions placeholder, allowed techniques, blast-radius cap, data-handling, window and authorizer placeholders' },
    outOfReach: { type: 'array', items: { type: 'string' }, description: 'surfaces Metasploit does not test (pure source bugs → qa-security, client-side, etc.)' },
  },
  required: ['workspace', 'setup', 'tests', 'scopeFileSkeleton'],
}

const MAPPING = [
  'Surface -> module guidance (confirm live with recon + check before run):',
  'SMB/445 -> auxiliary/scanner/smb/smb_ms17_010, exploit/windows/smb/ms17_010_*, smb_login (lockout-aware).',
  'HTTP app -> auxiliary/scanner/http/* then the framework-specific RCE exploit.',
  'Struts/Spring/Rails/Laravel -> exploit/multi/http/struts2_*/spring_*/rails_*/..._deserialization if the version matches.',
  'Log4j (any Java svc) -> auxiliary/scanner/http/log4shell_scanner then exploit/multi/http/log4shell_header_injection.',
  'SSH/22 -> auxiliary/scanner/ssh/ssh_login(_pubkey), bounded + lockout-aware.',
  'RDP/3389 -> auxiliary/scanner/rdp/*, exploit/windows/rdp/*.',
  'DBs (3306/5432/1433/27017/6379) -> auxiliary/scanner/<db>/<db>_login/_hashdump/_schemadump; never a dos module.',
  'WordPress/Drupal/Joomla -> auxiliary/scanner/http/wordpress_*, exploit/unix/webapp/*.',
  'CVE lead from a manifest -> search cve:<id> -> info -> check (strongest input).',
  'Payload: reverse_* when target can reach attacker (default); bind_* only with an inbound path. Stageless across flaky/filtered links; staged for smaller footprint. Set LPORT to an open egress port (443/53 often survive).',
].join('\n')

const plan = await agent(
  `${SAFETY}\n\nYou are planning an authorized Metasploit assessment of the DEPLOYMENT that the repository at "${repo}" produces. The deployed lab target the human will name: ${targetHint}.\n\n` +
  `Deploy profile (from three static readers):\n${JSON.stringify(profile, null, 2)}\n\n` +
  `Use this surface->module mapping:\n${MAPPING}\n\n` +
  `Produce: (1) the toolchain SETUP (Metasploit Docker image pinned by digest, an engagement-named msfdb workspace, the MCP server registered read-only; note if a lab deployment must be stood up); (2) a TEST plan — one entry per surface/CVE lead with a concrete module/search term, action (check-then-run / scan / cred-test), the exact operatorCommand the authorized human runs (use/set/check/run lines or the msfvenom line, LHOST/LPORT filled), payload shape, the single provenOutcome that counts (NEVER an OR), the MITRE ATT&CK id, and availabilityRisk=true for memory-corruption/manual-rank modules; (3) a docs/security/engagement-<NNN>.md SCOPE-FILE SKELETON pre-filled with the derived in-scope services/hosts, placeholders for hard exclusions, allowed techniques (match the planned modules), a blast-radius cap, data-handling, the window and the named authorizer; (4) outOfReach surfaces Metasploit does not cover (pure source bugs, client-side) routed elsewhere.\n` +
  `This is a plan handed to a human for authorization; it executes nothing. Every live act is operator-run (the human holds the authorization and runs the operatorCommand), so the plan's value is that each test is ready to paste and run. Rank tests by signal (a matched-version CVE lead beats a broad scan).`,
  { ...SONNET, label: 'plan:synthesize', phase: 'Plan', schema: PLAN_SCHEMA },
)

phase('Review')

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    missedSurfaces: { type: 'array', items: { type: 'string' }, description: 'exposed services/CVE leads in the profile the plan did not test' },
    overreach: { type: 'array', items: { type: 'string' }, description: 'planned tests that exceed Metasploit scope, risk availability without flagging it, or would touch something not in the profile' },
    gateIssues: { type: 'array', items: { type: 'string' }, description: 'ways the scope-file skeleton is under-specified or would allow an out-of-scope act' },
    addTests: {
      type: 'array',
      items: {
        type: 'object',
        properties: { surface: { type: 'string' }, module: { type: 'string' }, why: { type: 'string' } },
        required: ['surface', 'module', 'why'],
      },
    },
    verdict: { type: 'string', description: 'one line: is the plan complete and gate-safe, or what must change' },
  },
  required: ['verdict'],
}

const review = await agent(
  `${SAFETY}\n\nAdversarially review this Metasploit assessment plan for COMPLETENESS and GATE-SAFETY.\n\n` +
  `Deploy profile:\n${JSON.stringify(profile, null, 2)}\n\nPlan:\n${JSON.stringify(plan, null, 2)}\n\n` +
  `Find: (a) exposed services or matched-version CVE leads in the profile that the plan failed to test; (b) overreach — tests beyond Metasploit's scope, availability-risking modules not flagged, or anything touching a host not in the profile; (c) gate issues — ways the scope-file skeleton is under-specified or would permit an out-of-scope act; (d) specific tests to add. Default to skepticism. End with a one-line verdict.`,
  { ...SONNET, label: 'review:completeness', phase: 'Review', schema: REVIEW_SCHEMA },
)

return { profile, plan, review }
