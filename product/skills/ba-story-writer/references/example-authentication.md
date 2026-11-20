# Example — a complete story

`US1 Authentication`, the first story of an initiative whose epic `E1` is "people have their own account". Every number in it (12 characters, 24 hours, 60 minutes, five attempts, 15 minutes, 30 days) is a business rule from that initiative's `requirements.md` §4; none was chosen by the story's author.

```markdown
## US1 — Authentication

**Epic:** E1

### Goal
A person can create their own account and get back into it whenever they need to, and nobody else
can. Until this exists nothing in the product can belong to an individual, so every later feature
that shows "my" anything waits on it.

### How we get there
- People sign in with an email address and a password. Signing in through another provider
  (Google, Apple) was considered and deferred: the first customers are companies that issue
  work email addresses.
- The email address is proven before the account can be used. Registration creates the account
  unconfirmed and sends a link; opening the link confirms it.
- A forgotten password is never sent or shown. The person asks for a reset, gets a link by email
  and chooses a new password themselves.
- Registration comes first, because login and reset both need an account to exist. Login second,
  reset last.
- The company's existing identity provider is reused (requirements.md §5, stated by the CTO).

### What is included
- **Register with confirmation**: a person signs up with their name, email and a password, gets a
  confirmation email, and confirms the account by opening its link. They can ask for the email
  again.
- **Login**: a person with a confirmed account signs in with their email and password, stays
  signed in on that device, and can sign out. Repeated wrong attempts lock the account for a while.
- **Reset password via email**: a person who has forgotten their password asks for a reset link,
  opens it and sets a new password.

### Acceptance criteria

**Register with confirmation**
- **AC1** A person who gives a name, an email address not yet registered and a valid password gets
  an unconfirmed account and is told to check their email.
- **AC2** The confirmation email arrives within 2 minutes of registering.
- **AC3** Opening the confirmation link within 24 hours confirms the account.
- **AC4** A confirmation link older than 24 hours confirms nothing; it says it has expired and
  offers to send a new one.
- **AC5** A password shorter than 12 characters is refused, at registration and at reset, and the
  person is told the minimum.
- **AC6** Registering with an email address that already has an account creates nothing and shows
  the same "check your email" message as a new registration.

**Login**
- **AC7** A person with a confirmed account who enters their email and password is signed in and
  lands on their home page.
- **AC8** A wrong email or password is refused with one message that does not say which of the two
  was wrong.
- **AC9** A person whose account is not yet confirmed is not signed in; they are told to confirm
  and offered the email again.
- **AC10** After five wrong passwords in 15 minutes the account is locked for 15 minutes, and the
  person is told when they can try again.
- **AC11** A signed-in person stays signed in on that device for 30 days, or until they sign out.

**Reset password via email**
- **AC12** Asking for a reset shows the same message whether or not the email address has an
  account, and sends a link only when it does.
- **AC13** A reset link opened within 60 minutes lets the person set a new password.
- **AC14** A reset link that has been used, or is older than 60 minutes, sets nothing; it says so
  and offers a new one.
- **AC15** Once a new password is set the old one no longer works, and the person is signed out on
  every other device.

**Across the feature**
- **AC16** Every register, confirm, login, failed login, lockout and reset is recorded with the
  account, the time and the outcome, and the record never holds a password.

### Not included
- Signing in with Google or Apple: deferred to a later initiative (see How we get there).
- A second sign-in step by code or app: out of scope for this release, decided by the product
  owner.
- Changing the email address or deleting the account: US4 Account settings.

### Depends on
- none

### Source
requirements.md §4.1 (accounts), §4.2 (rules R1–R6: password length, link lifetimes, lockout,
session length), §5 (existing identity provider).
```

## What to read in it

- **The goal is not the title.** It says who, what they can do, and why the rest of the product waits on it.
- **How we get there is a plan, not a design.** It names the route (email and password, proof by link, reset by link), what was considered and set aside, the order, and the one imposed constraint by citing where the business stated it. No table, endpoint or screen appears.
- **What is included names three parts and says what each does**, including the pieces that are easy to forget: sending the confirmation again, signing out, the lockout.
- **Every part has criteria for when it works and for when it cannot.** AC1–AC3 against AC4–AC6; AC7 against AC8–AC10; AC13 against AC14.
- **Each criterion is one situation and what comes of it**, so someone else can mark it met or not met. The confirmation email arriving (AC2) and its link working (AC3) are two situations, so two criteria. None says "works", "secure" or "properly".
- **AC6 and AC12 state a rule the happy path hides**: the product never reveals whether an email address has an account.
